import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_authorizers as authorizers,
    aws_apigatewayv2_integrations as integrations,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
)
from constructs import Construct


def env_list(name: str, defaults: list[str]) -> list[str]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return defaults

    return [value.strip() for value in raw_value.split(",") if value.strip()]


class IsbnLibraryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region
        domain_prefix = os.getenv("COGNITO_DOMAIN_PREFIX", "isbn-library-dev")
        callback_urls = env_list(
            "COGNITO_CALLBACK_URLS",
            ["http://localhost:5173/auth/callback"],
        )
        logout_urls = env_list(
            "COGNITO_LOGOUT_URLS",
            ["http://localhost:5173"],
        )
        cors_origins = env_list(
            "CORS_ALLOW_ORIGINS",
            ["http://localhost:5173"],
        )

        books_table = dynamodb.Table(
            self,
            "BooksTable",
            table_name="books",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="isbn",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        user_pool = cognito.UserPool(
            self,
            "UserPool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
        )

        user_pool_client = user_pool.add_client(
            "UserPoolClient",
            generate_secret=False,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                ),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=callback_urls,
                logout_urls=logout_urls,
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )

        user_pool.add_domain(
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=domain_prefix,
            ),
        )

        jwt_issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool.user_pool_id}"
        hosted_ui_domain = f"https://{domain_prefix}.auth.{region}.amazoncognito.com"

        shared_layer = lambda_.LayerVersion(
            self,
            "SharedLayer",
            code=lambda_.Code.from_asset("../backend/lambda/shared"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities for ISBN Library lambdas",
        )

        common_environment = {
            "BOOKS_TABLE_NAME": books_table.table_name,
        }

        common_lambda_props = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "timeout": Duration.seconds(15),
            "memory_size": 256,
            "layers": [shared_layer],
            "environment": common_environment,
        }

        get_books_lambda = lambda_.Function(
            self,
            "GetBooksLambda",
            code=lambda_.Code.from_asset("../backend/lambda/get_books"),
            handler="handler.handler",
            **common_lambda_props,
        )

        get_book_lambda = lambda_.Function(
            self,
            "GetBookLambda",
            code=lambda_.Code.from_asset("../backend/lambda/get_book"),
            handler="handler.handler",
            **common_lambda_props,
        )

        create_book_lambda = lambda_.Function(
            self,
            "CreateBookLambda",
            code=lambda_.Code.from_asset("../backend/lambda/create_book"),
            handler="handler.handler",
            **common_lambda_props,
        )

        delete_book_lambda = lambda_.Function(
            self,
            "DeleteBookLambda",
            code=lambda_.Code.from_asset("../backend/lambda/delete_book"),
            handler="handler.handler",
            **common_lambda_props,
        )

        lookup_book_lambda = lambda_.Function(
            self,
            "LookupBookLambda",
            code=lambda_.Code.from_asset("../backend/lambda/lookup_book"),
            handler="handler.handler",
            **common_lambda_props,
        )

        books_table.grant_read_data(get_books_lambda)
        books_table.grant_read_data(get_book_lambda)
        books_table.grant_read_write_data(create_book_lambda)
        books_table.grant_read_write_data(delete_book_lambda)

        http_api = apigatewayv2.HttpApi(
            self,
            "BooksHttpApi",
            cors_preflight=apigatewayv2.CorsPreflightOptions(
                allow_headers=["Authorization", "Content-Type"],
                allow_methods=[
                    apigatewayv2.CorsHttpMethod.GET,
                    apigatewayv2.CorsHttpMethod.POST,
                    apigatewayv2.CorsHttpMethod.DELETE,
                    apigatewayv2.CorsHttpMethod.OPTIONS,
                ],
                allow_origins=cors_origins,
            ),
        )

        jwt_authorizer = authorizers.HttpJwtAuthorizer(
            "BooksJwtAuthorizer",
            jwt_issuer=jwt_issuer,
            jwt_audience=[user_pool_client.user_pool_client_id],
        )

        http_api.add_routes(
            path="/books",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration(
                "GetBooksIntegration", get_books_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/books/{isbn}",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration(
                "GetBookIntegration", get_book_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/books",
            methods=[apigatewayv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration(
                "CreateBookIntegration", create_book_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/books/{isbn}",
            methods=[apigatewayv2.HttpMethod.DELETE],
            integration=integrations.HttpLambdaIntegration(
                "DeleteBookIntegration", delete_book_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/lookup/{isbn}",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration(
                "LookupBookIntegration", lookup_book_lambda
            ),
            authorizer=jwt_authorizer,
        )

        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "CognitoDomain", value=hosted_ui_domain)
        CfnOutput(self, "ApiUrl", value=http_api.url or "")
        CfnOutput(self, "JwtIssuer", value=jwt_issuer)
        CfnOutput(self, "BooksTableName", value=books_table.table_name)
