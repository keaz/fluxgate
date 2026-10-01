#!/usr/bin/env node

/**
 * Generate Postman Performance Test Data Files
 *
 * Creates CSV files with test data for Postman's performance testing.
 * Uses weighted Pareto distribution (80/20 rule) for realistic traffic simulation.
 *
 * Usage:
 *   node generate-postman-data.js
 *
 * Generates:
 *   - postman-data-100f.csv (100 features)
 *   - postman-data-400f.csv (400 features)
 *   - postman-data-1000f.csv (1000 features)
 */

import fs from 'fs';

// Configuration
const ENVIRONMENT_ID = 'b0ef91fd-a92c-45f8-ae5f-1a8c7f97b12f';
const FEATURE_COUNTS = [100, 400, 1000];
const REQUESTS_PER_FILE = 1000; // Number of test requests to generate
const FEATURE_START_INDEX = 10000; // Start features from feature=10000

// Context data pools (realistic values)
const REGIONS = ['us-east', 'us-west', 'eu-west', 'eu-central', 'ap-south', 'ap-northeast', 'sa-east'];
const TIERS = ['free', 'basic', 'pro', 'enterprise'];
const ROLES = ['viewer', 'editor', 'admin', 'owner'];
const DEVICE_TYPES = ['mobile', 'tablet', 'desktop', 'tv'];
const OS_TYPES = ['ios', 'android', 'windows', 'macos', 'linux'];
const APP_VERSIONS = ['v1.0', 'v1.1', 'v1.2', 'v2.0', 'v2.1', 'v2.2', 'v3.0'];
const LANGUAGES = ['en', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'ru', 'ar', 'hi'];
const COUNTRIES = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR', 'MX', 'ES'];
const BETA_FLAGS = ['true', 'false'];

// Helper functions
function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min)) + min;
}

function randomElement(array) {
  return array[randomInt(0, array.length)];
}

/**
 * Generate feature key using weighted Pareto distribution (80/20 rule)
 * 80% of requests go to top 20% of features (hot features)
 * 20% of requests go to remaining 80% of features (cold features)
 */
function getWeightedFeatureKey(maxFeatures) {
  const hotFeatureCount = Math.floor(maxFeatures * 0.2); // Top 20%
  const randomValue = Math.random();

  if (randomValue < 0.8) {
    // 80% of requests - select from hot features (10000 to 10000+19% of range)
    return `feature=${FEATURE_START_INDEX + randomInt(0, hotFeatureCount)}`;
  } else {
    // 20% of requests - select from cold features (10000+20% to 10000+100% of range)
    return `feature=${FEATURE_START_INDEX + randomInt(hotFeatureCount, maxFeatures)}`;
  }
}

/**
 * Generate random user ID for bucketing
 */
function generateUserId() {
  return `user-${randomInt(1, 100000)}`;
}

/**
 * Generate random context attributes
 */
function generateContextAttributes() {
  return {
    region: randomElement(REGIONS),
    tier: randomElement(TIERS),
    userRole: randomElement(ROLES),
    deviceType: randomElement(DEVICE_TYPES),
    osType: randomElement(OS_TYPES),
    appVersion: randomElement(APP_VERSIONS),
    language: randomElement(LANGUAGES),
    country: randomElement(COUNTRIES),
    beta: randomElement(BETA_FLAGS),
    timestamp: Date.now()
  };
}

/**
 * Generate a single test request row
 */
function generateRequestRow(maxFeatures) {
  const featureKey = getWeightedFeatureKey(maxFeatures);
  const bucketingKey = generateUserId();
  const context = generateContextAttributes();

  return {
    flagKey: featureKey,
    environmentId: ENVIRONMENT_ID,
    bucketingKey: bucketingKey,
    region: context.region,
    tier: context.tier,
    userRole: context.userRole,
    deviceType: context.deviceType,
    osType: context.osType,
    appVersion: context.appVersion,
    language: context.language,
    country: context.country,
    beta: context.beta,
    timestamp: context.timestamp
  };
}

/**
 * Generate CSV file for Postman
 */
function generateCSV(featureCount, requestCount) {
  const filename = `postman-data-${featureCount}f.csv`;
  const rows = [];

  // CSV Header
  const header = [
    'flagKey',
    'environmentId',
    'bucketingKey',
    'region',
    'tier',
    'userRole',
    'deviceType',
    'osType',
    'appVersion',
    'language',
    'country',
    'beta',
    'timestamp'
  ];

  rows.push(header.join(','));

  // Generate data rows
  for (let i = 0; i < requestCount; i++) {
    const row = generateRequestRow(featureCount);
    const csvRow = [
      row.flagKey,
      row.environmentId,
      row.bucketingKey,
      row.region,
      row.tier,
      row.userRole,
      row.deviceType,
      row.osType,
      row.appVersion,
      row.language,
      row.country,
      row.beta,
      row.timestamp
    ];
    rows.push(csvRow.join(','));
  }

  // Write to file
  const csvContent = rows.join('\n');
  fs.writeFileSync(filename, csvContent, 'utf8');

  return filename;
}

/**
 * Generate statistics about the distribution
 */
function generateStatistics(featureCount, requestCount) {
  const featureHits = new Map();

  // Simulate distribution
  for (let i = 0; i < requestCount; i++) {
    const featureKey = getWeightedFeatureKey(featureCount);
    featureHits.set(featureKey, (featureHits.get(featureKey) || 0) + 1);
  }

  // Calculate hot vs cold distribution
  const hotThreshold = Math.floor(featureCount * 0.2);
  const hotFeatureMax = FEATURE_START_INDEX + hotThreshold;
  let hotHits = 0;
  let coldHits = 0;

  featureHits.forEach((hits, featureKey) => {
    const featureNum = parseInt(featureKey.split('=')[1]);
    if (featureNum < hotFeatureMax) {
      hotHits += hits;
    } else {
      coldHits += hits;
    }
  });

  return {
    totalRequests: requestCount,
    uniqueFeatures: featureHits.size,
    hotFeatures: hotThreshold,
    coldFeatures: featureCount - hotThreshold,
    hotFeatureRange: `${FEATURE_START_INDEX}-${hotFeatureMax - 1}`,
    coldFeatureRange: `${hotFeatureMax}-${FEATURE_START_INDEX + featureCount - 1}`,
    hotHits: hotHits,
    coldHits: coldHits,
    hotPercentage: ((hotHits / requestCount) * 100).toFixed(2),
    coldPercentage: ((coldHits / requestCount) * 100).toFixed(2)
  };
}

// Main execution
console.log('='.repeat(80));
console.log('Postman Performance Test Data Generator');
console.log('='.repeat(80));
console.log('');
console.log('Configuration:');
console.log(`  Environment ID:    ${ENVIRONMENT_ID}`);
console.log(`  Requests per file: ${REQUESTS_PER_FILE}`);
console.log(`  Distribution:      Weighted Pareto (80/20 rule)`);
console.log('');

// Generate files for each feature count
FEATURE_COUNTS.forEach(featureCount => {
  console.log('-'.repeat(80));
  console.log(`Generating data for ${featureCount} features...`);

  const filename = generateCSV(featureCount, REQUESTS_PER_FILE);
  const stats = generateStatistics(featureCount, REQUESTS_PER_FILE);

  console.log(`  ✓ File created: ${filename}`);
  console.log('');
  console.log('  Distribution Statistics:');
  console.log(`    Total Requests:      ${stats.totalRequests}`);
  console.log(`    Unique Features Hit: ${stats.uniqueFeatures}/${featureCount}`);
  console.log('');
  console.log('  Feature Segmentation:');
  console.log(`    Hot Features:        ${stats.hotFeatures} (20% of total)`);
  console.log(`    Hot Feature Range:   feature=${stats.hotFeatureRange}`);
  console.log(`    Cold Features:       ${stats.coldFeatures} (80% of total)`);
  console.log(`    Cold Feature Range:  feature=${stats.coldFeatureRange}`);
  console.log('');
  console.log('  Traffic Distribution:');
  console.log(`    Hot Feature Hits:    ${stats.hotHits} (${stats.hotPercentage}%)`);
  console.log(`    Cold Feature Hits:   ${stats.coldHits} (${stats.coldPercentage}%)`);
  console.log('');
});

console.log('='.repeat(80));
console.log('✓ All data files generated successfully!');
console.log('='.repeat(80));
console.log('');
console.log('Next Steps:');
console.log('  1. Import CSV file into Postman Collection Runner');
console.log('  2. Map CSV columns to request variables (see POSTMAN_SETUP.md)');
console.log('  3. Run performance test');
console.log('');
console.log('Files:');
console.log('  - postman-data-100f.csv   (100 features, 1000 requests)');
console.log('  - postman-data-400f.csv   (400 features, 1000 requests)');
console.log('  - postman-data-1000f.csv  (1000 features, 1000 requests)');
console.log('');
