#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DepartureBoardStack } from '../lib/departure-board-stack';

const app = new cdk.App();
new DepartureBoardStack(app, 'DepartureBoardStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'eu-north-1',
  },
});
