<?php

$outputDir = __DIR__ . '/../output';
if (!is_dir($outputDir)) {
    mkdir($outputDir, 0777, true);
}

$summary = [
    'products' => 0,
    'variableProducts' => 0,
    'variations' => 0,
    // Count the distinct imported departments represented by current products.
    'departments' => 0,
    // Count the distinct collection keys represented by current products.
    'collections' => 0,
    'shippingZones' => 0,
    'paymentGateways' => 0,
    'launchFeedCount' => 0,
];

file_put_contents(
    $outputDir . '/seed-summary.json',
    json_encode($summary, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL
);

fwrite(STDOUT, "seeded placeholder summary\n");
