import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';

export class DockerLambdaAwsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define an IAM role for the Lambda functions
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        // Add any additional managed policies you need
      ],
    });

    // Add additional permissions to the role as needed
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      resources: ['*'],
      actions: [
        's3:*',
        'dynamodb:*',
        'logs:*',
        'cloudwatch:*',
        'lambda:*',
        // Add any other actions you need
      ],
    }));

    // Define the first Lambda function with a Docker image
    const dockerFunc1 = new lambda.DockerImageFunction(this, 'DockerFunc1', {
      functionName: 'Document-Preprocessor', // Name the function
      code: lambda.DockerImageCode.fromImageAsset('./function-1'),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(100),
      architecture: lambda.Architecture.X86_64,
      role: lambdaRole, // Attach the role to the Lambda function
    });

    const functionUrl1 = dockerFunc1.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedMethods: [lambda.HttpMethod.ALL],
        allowedHeaders: ['*'],
        allowedOrigins: ['*'],
      },
    });

    new cdk.CfnOutput(this, 'FunctionUrl1', {
      value: functionUrl1.url,
    });

    // Define the second Lambda function with a Docker image
    const dockerFunc2 = new lambda.DockerImageFunction(this, 'DockerFunc2', {
      functionName: 'Chunk-Embedder', // Name the function
      code: lambda.DockerImageCode.fromImageAsset('./function-2'),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(100),
      architecture: lambda.Architecture.X86_64,
      role: lambdaRole, // Attach the role to the Lambda function
    });

    const functionUrl2 = dockerFunc2.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedMethods: [lambda.HttpMethod.ALL],
        allowedHeaders: ['*'],
        allowedOrigins: ['*'],
      },
    });

    new cdk.CfnOutput(this, 'FunctionUrl2', {
      value: functionUrl2.url,
    });
  }
}
