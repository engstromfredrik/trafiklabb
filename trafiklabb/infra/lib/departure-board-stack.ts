import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as path from 'path';

export class DepartureBoardStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // --- Lambda Functions ---
    const sitesFunction = new lambda.Function(this, 'SitesFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.search_sites',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend')),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
    });

    const departuresFunction = new lambda.Function(this, 'DeparturesFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.get_departures',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend')),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
    });

    // --- API Gateway ---
    const api = new apigateway.RestApi(this, 'DepartureBoardApi', {
      restApiName: 'DepartureBoard',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type'],
      },
    });

    // GET /api/sites
    const apiResource = api.root.addResource('api');
    const sitesResource = apiResource.addResource('sites');
    sitesResource.addMethod('GET', new apigateway.LambdaIntegration(sitesFunction));

    // GET /api/sites/{siteId}/departures
    const siteIdResource = sitesResource.addResource('{siteId}');
    const departuresResource = siteIdResource.addResource('departures');
    departuresResource.addMethod('GET', new apigateway.LambdaIntegration(departuresFunction));

    // --- Custom Domain ---
    const domainName = 'departures.engstrom.cloud';
    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'EngstromZone', {
      hostedZoneId: 'Z02189273AOR9DCFLK4K',
      zoneName: 'engstrom.cloud',
    });

    const certificate = new acm.DnsValidatedCertificate(this, 'SiteCertificate', {
      domainName,
      hostedZone,
      region: 'us-east-1',
    });

    // --- S3 Bucket for Frontend ---
    const websiteBucket = new s3.Bucket(this, 'FrontendBucket', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // --- CloudFront Distribution ---
    const distribution = new cloudfront.Distribution(this, 'FrontendDistribution', {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(websiteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      defaultRootObject: 'index.html',
      domainNames: [domainName],
      certificate,
    });

    // --- Route 53 Alias Record ---
    new route53.ARecord(this, 'SiteAliasRecord', {
      zone: hostedZone,
      recordName: domainName,
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
    });

    // --- Deploy Frontend to S3 ---
    new s3deploy.BucketDeployment(this, 'DeployFrontend', {
      sources: [s3deploy.Source.asset(path.join(__dirname, '../../frontend'))],
      destinationBucket: websiteBucket,
      distribution,
      distributionPaths: ['/*'],
    });

    // --- Outputs ---
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'API Gateway endpoint URL',
    });

    new cdk.CfnOutput(this, 'CloudFrontUrl', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'CloudFront website URL',
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: websiteBucket.bucketName,
      description: 'S3 bucket name for frontend',
    });
  }
}
