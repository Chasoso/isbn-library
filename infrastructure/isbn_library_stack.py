import os
import shutil
import subprocess
import sys
from pathlib import Path

import jsii
from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    ILocalBundling,
    RemovalPolicy,
    Stack,
    TimeZone,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_authorizers as authorizers,
    aws_apigatewayv2_integrations as integrations,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_scheduler as scheduler,
    aws_scheduler_targets as scheduler_targets,
    aws_ssm as ssm,
)
from constructs import Construct


def env_list(name: str, defaults: list[str]) -> list[str]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return defaults

    return [value.strip() for value in raw_value.split(",") if value.strip()]


@jsii.implements(ILocalBundling)
class PythonLayerLocalBundling:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    def try_bundle(self, output_dir: str, _options: BundlingOptions) -> bool:
        output_path = Path(output_dir)
        shutil.copytree(self.source_path, output_path, dirs_exist_ok=True)

        requirements_path = self.source_path / "requirements.txt"
        if requirements_path.exists():
            python_dir = output_path / "python"
            python_dir.mkdir(parents=True, exist_ok=True)
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_path),
                    "-t",
                    str(python_dir),
                ]
            )

        return True


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
        google_books_api_key = os.getenv("GOOGLE_BOOKS_API_KEY", "")
        books_table_name = os.getenv("BOOKS_TABLE_NAME", "books")
        categories_table_name = os.getenv("CATEGORIES_TABLE_NAME", "book-category")
        google_wif_credential_config_parameter_name = os.getenv(
            "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME",
            "",
        )
        google_sheets_spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
        google_sheets_books_sheet_name = os.getenv("GOOGLE_SHEETS_BOOKS_SHEET_NAME", "books")
        google_sheets_categories_sheet_name = os.getenv(
            "GOOGLE_SHEETS_CATEGORIES_SHEET_NAME",
            "categories",
        )
        export_schedule_expression = os.getenv(
            "BOOKS_EXPORT_SCHEDULE_EXPRESSION",
            "cron(0 3 * * ? *)",
        )
        export_schedule_timezone = os.getenv(
            "BOOKS_EXPORT_SCHEDULE_TIMEZONE",
            "Asia/Tokyo",
        )

        books_table = dynamodb.Table(
            self,
            "BooksTable",
            table_name=books_table_name,
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

        categories_table = dynamodb.Table(
            self,
            "CategoriesTable",
            table_name=categories_table_name,
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="categoryId",
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

        shared_layer_source = Path(__file__).resolve().parent.parent / "backend" / "lambda" / "shared"
        shared_layer = lambda_.LayerVersion(
            self,
            "SharedLayer",
            code=lambda_.Code.from_asset(
                str(shared_layer_source),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    local=PythonLayerLocalBundling(shared_layer_source),
                    command=[
                        "bash",
                        "-c",
                        "cp -r . /asset-output && python -m pip install -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities for ISBN Library lambdas",
        )

        common_environment = {
            "BOOKS_TABLE_NAME": books_table.table_name,
            "CATEGORIES_TABLE_NAME": categories_table.table_name,
            "GOOGLE_BOOKS_API_KEY": google_books_api_key,
            "GOOGLE_WIF_CREDENTIAL_CONFIG_PARAMETER_NAME": google_wif_credential_config_parameter_name,
            "GOOGLE_SHEETS_SPREADSHEET_ID": google_sheets_spreadsheet_id,
            "GOOGLE_SHEETS_BOOKS_SHEET_NAME": google_sheets_books_sheet_name,
            "GOOGLE_SHEETS_CATEGORIES_SHEET_NAME": google_sheets_categories_sheet_name,
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
        update_book_status_lambda = lambda_.Function(
            self,
            "UpdateBookStatusLambda",
            code=lambda_.Code.from_asset("../backend/lambda/update_book_status"),
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
        get_categories_lambda = lambda_.Function(
            self,
            "GetCategoriesLambda",
            code=lambda_.Code.from_asset("../backend/lambda/get_categories"),
            handler="handler.handler",
            **common_lambda_props,
        )
        create_category_lambda = lambda_.Function(
            self,
            "CreateCategoryLambda",
            code=lambda_.Code.from_asset("../backend/lambda/create_category"),
            handler="handler.handler",
            **common_lambda_props,
        )
        update_category_lambda = lambda_.Function(
            self,
            "UpdateCategoryLambda",
            code=lambda_.Code.from_asset("../backend/lambda/update_category"),
            handler="handler.handler",
            **common_lambda_props,
        )
        export_books_to_sheets_lambda = lambda_.Function(
            self,
            "ExportBooksToSheetsLambda",
            code=lambda_.Code.from_asset("../backend/lambda/export_books_to_sheets"),
            handler="handler.handler",
            timeout=Duration.seconds(60),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[shared_layer],
            environment=common_environment,
        )

        for fn in [
            get_books_lambda,
            get_book_lambda,
            create_book_lambda,
            delete_book_lambda,
            update_book_status_lambda,
            export_books_to_sheets_lambda,
        ]:
            books_table.grant_read_write_data(fn)

        for fn in [
            get_books_lambda,
            get_book_lambda,
            create_book_lambda,
            get_categories_lambda,
            create_category_lambda,
            update_category_lambda,
            update_book_status_lambda,
            export_books_to_sheets_lambda,
        ]:
            categories_table.grant_read_write_data(fn)

        if google_wif_credential_config_parameter_name:
            google_wif_credential_config_parameter = ssm.StringParameter.from_string_parameter_name(
                self,
                "GoogleWifCredentialConfigParameter",
                google_wif_credential_config_parameter_name,
            )
            google_wif_credential_config_parameter.grant_read(export_books_to_sheets_lambda)

        http_api = apigatewayv2.HttpApi(
            self,
            "BooksHttpApi",
            cors_preflight=apigatewayv2.CorsPreflightOptions(
                allow_headers=["Authorization", "Content-Type"],
                allow_methods=[
                    apigatewayv2.CorsHttpMethod.GET,
                    apigatewayv2.CorsHttpMethod.POST,
                    apigatewayv2.CorsHttpMethod.PATCH,
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
            path="/books/{isbn}/status",
            methods=[apigatewayv2.HttpMethod.PATCH],
            integration=integrations.HttpLambdaIntegration(
                "UpdateBookStatusIntegration", update_book_status_lambda
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
        http_api.add_routes(
            path="/categories",
            methods=[apigatewayv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration(
                "GetCategoriesIntegration", get_categories_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/categories",
            methods=[apigatewayv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration(
                "CreateCategoryIntegration", create_category_lambda
            ),
            authorizer=jwt_authorizer,
        )
        http_api.add_routes(
            path="/categories/{categoryId}",
            methods=[apigatewayv2.HttpMethod.PATCH],
            integration=integrations.HttpLambdaIntegration(
                "UpdateCategoryIntegration", update_category_lambda
            ),
            authorizer=jwt_authorizer,
        )

        if (
            google_wif_credential_config_parameter_name
            and google_sheets_spreadsheet_id
            and export_schedule_expression
        ):
            scheduler.Schedule(
                self,
                "BooksExportSchedule",
                schedule=scheduler.ScheduleExpression.expression(
                    export_schedule_expression,
                    time_zone=TimeZone.of(export_schedule_timezone),
                ),
                target=scheduler_targets.LambdaInvoke(
                    export_books_to_sheets_lambda,
                ),
                description="Daily export of books and categories to Google Sheets",
            )

        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "CognitoDomain", value=hosted_ui_domain)
        CfnOutput(self, "ApiUrl", value=http_api.url or "")
        CfnOutput(self, "JwtIssuer", value=jwt_issuer)
        CfnOutput(self, "BooksTableName", value=books_table.table_name)
        CfnOutput(self, "CategoriesTableName", value=categories_table.table_name)
        CfnOutput(self, "BooksExportFunctionName", value=export_books_to_sheets_lambda.function_name)
