#!/usr/bin/env python3
import aws_cdk as cdk

from isbn_library_stack import IsbnLibraryStack


app = cdk.App()
IsbnLibraryStack(app, "IsbnLibraryStack")
app.synth()
