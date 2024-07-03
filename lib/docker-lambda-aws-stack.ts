import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3Notifications from 'aws-cdk-lib/aws-s3-notifications';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';

export class DockerLambdaAwsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create a VPC for the Redis cluster and Lambda functions
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2, 
    });

    // Create a subnet group for the Redis cluster
    const subnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'Subnet group for Redis cluster',
      subnetIds: vpc.selectSubnets({ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }).subnetIds,
    });

    // Security group for Redis
    const redisSecurityGroup = new ec2.SecurityGroup(this, 'RedisSecurityGroup', {
      vpc,
      allowAllOutbound: true,
      description: 'Security group for Redis cluster',
    });
    redisSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(6379), 'Allow Redis traffic');

    // Security group for Lambda
    const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc,
      allowAllOutbound: true,
      description: 'Security group for Lambda functions',
    });
    lambdaSecurityGroup.addIngressRule(redisSecurityGroup, ec2.Port.tcp(6379), 'Allow Lambda to access Redis');

    // Create the Redis cluster
    const redisCluster = new elasticache.CfnCacheCluster(this, 'RedisCluster', {
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      numCacheNodes: 1,
      clusterName: 'my-redis-cluster',
      vpcSecurityGroupIds: [redisSecurityGroup.securityGroupId],
      cacheSubnetGroupName: subnetGroup.ref,
    });

    // Output the Redis cluster endpoint
    const redisEndpoint = new cdk.CfnOutput(this, 'RedisEndpoint', {
      value: redisCluster.attrRedisEndpointAddress,
    });

    // Create an IAM role for the Lambda functions
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      resources: ['*'],
      actions: [
        's3:*',
        'dynamodb:*',
        'logs:*',
        'cloudwatch:*',
        'lambda:*',
        'ec2:*',

      ],
    }));

    // Define the first Lambda function (Document-Preprocessor)
    const dockerFunc1 = new lambda.DockerImageFunction(this, 'DockerFunc1', {
      functionName: 'Document-Preprocessor',
      code: lambda.DockerImageCode.fromImageAsset('./Preprocessor'),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(100),
      architecture: lambda.Architecture.X86_64,
      role: lambdaRole,
      vpc,
      securityGroups: [lambdaSecurityGroup],
    });

    // Define an S3 bucket
    const documentBucket = new s3.Bucket(this, 'DocumentBucket', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    documentBucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3Notifications.LambdaDestination(dockerFunc1));

    // Output the bucket name for reference
    new cdk.CfnOutput(this, 'DocumentBucketName', {
      value: documentBucket.bucketName,
    });

    // Output the function URL for the first Lambda function
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

    // Define the second Lambda function (Chunk-Embedder)
    const dockerFunc2 = new lambda.DockerImageFunction(this, 'DockerFunc2', {
      functionName: 'Chunk-Embedder',
      code: lambda.DockerImageCode.fromImageAsset('./Embedder'),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(100),
      architecture: lambda.Architecture.X86_64,
      role: lambdaRole,
      vpc,
      securityGroups: [lambdaSecurityGroup],
    });

    // Add environment variables to the Chunk-Embedder Lambda function
    dockerFunc2.addEnvironment('REDIS_HOST', redisCluster.attrRedisEndpointAddress);
    dockerFunc2.addEnvironment('REDIS_PORT', '6379');

    // Output the function URL for the second Lambda function
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
