<?php

if (!defined('ABSPATH')) {
    exit;
}

function harbor_printshop_data_root(): string
{
    return '/app/data';
}

function harbor_printshop_read_json(string $file): array
{
    $path = harbor_printshop_data_root() . '/' . $file;
    $raw = file_get_contents($path);
    return $raw ? json_decode($raw, true, 512, JSON_THROW_ON_ERROR) : [];
}

function harbor_printshop_read_seed_rows(): array
{
    $rows = [];
    $path = harbor_printshop_data_root() . '/met_print_seed.csv';
    if (!file_exists($path)) {
        return $rows;
    }

    $handle = fopen($path, 'rb');
    if ($handle === false) {
        return $rows;
    }

    $header = fgetcsv($handle);
    if ($header === false) {
        fclose($handle);
        return $rows;
    }

    while (($row = fgetcsv($handle)) !== false) {
        $rows[] = array_combine($header, $row);
    }

    fclose($handle);
    return $rows;
}

function harbor_printshop_read_details_map(): array
{
    $map = [];
    $path = harbor_printshop_data_root() . '/met_object_details.ndjson';
    if (!file_exists($path)) {
        return $map;
    }

    $handle = fopen($path, 'rb');
    if ($handle === false) {
        return $map;
    }

    while (($line = fgets($handle)) !== false) {
        $decoded = json_decode($line, true, 512, JSON_THROW_ON_ERROR);
        $map[(int) $decoded['objectID']] = $decoded;
    }

    fclose($handle);
    return $map;
}

function harbor_printshop_collection_plan(): array
{
    return harbor_printshop_read_json('collection_plan.json');
}

function harbor_printshop_shipping_rules(): array
{
    return harbor_printshop_read_json('shipping_rules.json');
}

function harbor_printshop_checkout_policy(): array
{
    $path = harbor_printshop_data_root() . '/checkout_policy.md';
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [];
    $policy = [];
    foreach ($lines as $line) {
        if (!str_starts_with(trim($line), '- ')) {
            continue;
        }
        [$key, $value] = array_map('trim', explode(':', substr(trim($line), 2), 2));
        $policy[$key] = $value;
    }
    return $policy;
}

function harbor_printshop_seed_users(): array
{
    return harbor_printshop_read_json('seed_users.json')['users'] ?? [];
}

function harbor_printshop_collection_lookup(): array
{
    $lookup = [];
    $plan = harbor_printshop_collection_plan();
    foreach ($plan['collections'] ?? [] as $collection) {
        $lookup[$collection['key']] = $collection;
    }
    return $lookup;
}

function harbor_printshop_size_options(): array
{
    return harbor_printshop_collection_plan()['size_attribute']['options'] ?? [];
}

function harbor_printshop_launch_contract(): array
{
    return harbor_printshop_collection_plan()['launch_feed'] ?? [];
}

function harbor_printshop_size_option_by_key(string $key): ?array
{
    foreach (harbor_printshop_size_options() as $option) {
        if ($option['key'] === $key) {
            return $option;
        }
    }
    return null;
}

function harbor_printshop_parse_bool(mixed $value): bool
{
    return filter_var($value, FILTER_VALIDATE_BOOLEAN);
}

function harbor_printshop_build_seed_model(): array
{
    $rows = harbor_printshop_read_seed_rows();
    $detailsMap = harbor_printshop_read_details_map();
    $collections = harbor_printshop_collection_lookup();
    $model = [];

    foreach ($rows as $row) {
        $objectId = (int) $row['objectID'];
        if (!isset($detailsMap[$objectId])) {
            continue;
        }

        $detail = $detailsMap[$objectId];
        $collection = $collections[$row['collectionKey']] ?? null;
        $variations = [];
        foreach (harbor_printshop_size_options() as $option) {
            $stockColumn = $option['key'] . 'Stock';
            $stock = isset($row[$stockColumn]) ? (int) $row[$stockColumn] : 0;
            $variations[] = [
                'key' => $option['key'],
                'label' => $option['label'],
                'sku' => sprintf('MET-%d-%s', $objectId, $option['sku_suffix']),
                'price' => (float) $row['basePrice'] + (float) $option['price_delta'],
                'stock' => $stock,
                'shipping_class' => $option['shipping_class'],
                'in_stock' => $stock > 0,
            ];
        }

        $model[] = [
            'object_id' => $objectId,
            'department_slug' => $row['departmentSlug'],
            'department_name' => $detail['department'],
            'collection_key' => $row['collectionKey'],
            'collection_title' => $collection['title'] ?? $row['collectionKey'],
            'collection_sort_order' => (int) ($collection['sort_order'] ?? 999),
            'merchandising_title' => $row['merchandisingTitle'],
            'launch_state' => $row['launchState'],
            'featured_rank' => (int) $row['featuredRank'],
            'base_price' => (float) $row['basePrice'],
            'public_domain_clearance' => harbor_printshop_parse_bool($row['publicDomainClearance']),
            'detail' => $detail,
            'slug' => sanitize_title($row['merchandisingTitle']) . '-' . $objectId,
            'variations' => $variations,
        ];
    }

    return $model;
}

function harbor_printshop_pick_feed_variation(WC_Product_Variable $product): ?WC_Product_Variation
{
    $children = $product->get_children();
    $candidateMap = [];
    foreach ($children as $childId) {
        $variation = wc_get_product($childId);
        if (!$variation instanceof WC_Product_Variation) {
            continue;
        }
        $sizeKey = (string) $variation->get_meta('harbor_size_key', true);
        $candidateMap[$sizeKey] = $variation;
    }

    $options = harbor_printshop_size_options();
    if ($options === []) {
        return null;
    }

    $primaryKey = (string) $options[0]['key'];
    if (isset($candidateMap[$primaryKey])) {
        return $candidateMap[$primaryKey];
    }

    return null;
}

function harbor_printshop_has_any_in_stock_variation(WC_Product_Variable $product): bool
{
    foreach ($product->get_children() as $childId) {
        $variation = wc_get_product($childId);
        if ($variation instanceof WC_Product_Variation && $variation->get_stock_quantity() > 0) {
            return true;
        }
    }

    return false;
}

function harbor_printshop_build_launch_feed_items(bool $inStockOnly = false): array
{
    $contract = harbor_printshop_launch_contract();
    $products = wc_get_products([
        'status' => ['publish'],
        'type' => ['variable'],
        'limit' => -1,
        'orderby' => 'date',
        'order' => 'ASC',
    ]);

    $items = [];
    foreach ($products as $product) {
        if (!$product instanceof WC_Product_Variable) {
            continue;
        }
        $clearance = harbor_printshop_parse_bool($product->get_meta('harbor_public_domain_clearance', true));
        $image = (string) $product->get_meta('harbor_primary_image', true);
        $collectionKey = (string) $product->get_meta('harbor_collection_key', true);
        $launchState = (string) $product->get_meta('harbor_launch_state', true);
        $featuredRank = (int) $product->get_meta('harbor_featured_rank', true);
        $collectionSort = (int) $product->get_meta('harbor_collection_sort_order', true);
        $department = (string) $product->get_meta('harbor_department_slug', true);

        $variation = harbor_printshop_pick_feed_variation($product);
        $stockQty = $variation ? (int) $variation->get_stock_quantity() : 0;
        $available = $stockQty > 0;
        $hasAnyInStockVariation = harbor_printshop_has_any_in_stock_variation($product);

        if ($launchState !== ($contract['require_launch_state'] ?? 'publish')) {
            continue;
        }
        if (($contract['require_public_domain_clearance'] ?? false) && !$clearance) {
            continue;
        }
        if (($contract['require_primary_image'] ?? false) && $image === '') {
            continue;
        }
        if (($contract['require_in_stock_variation'] ?? false) && !$hasAnyInStockVariation) {
            continue;
        }
        if ($inStockOnly && !$available) {
            continue;
        }

        $items[] = [
            'productId' => $product->get_id(),
            'title' => $product->get_name(),
            'slug' => $product->get_slug(),
            'artistName' => (string) $product->get_meta('harbor_artist_name', true),
            'department' => $department,
            'collection' => $collectionKey,
            'collectionTitle' => (string) $product->get_meta('harbor_collection_title', true),
            'sku' => $variation ? $variation->get_sku() : '',
            'price' => $variation ? wc_format_decimal($variation->get_price(), 2) : '',
            'image' => $image,
            'availability' => $available ? 'in_stock' : 'out_of_stock',
            'featuredRank' => $featuredRank,
            'collectionSortOrder' => $collectionSort,
        ];
    }

    usort($items, function (array $a, array $b): int {
        return [$a['collectionSortOrder'], $a['featuredRank'], $a['productId']]
            <=> [$b['collectionSortOrder'], $b['featuredRank'], $b['productId']];
    });

    return $items;
}

function harbor_printshop_filter_feed_items(array $items, array $params): array
{
    $department = isset($params['department']) ? sanitize_text_field((string) $params['department']) : '';
    $collection = isset($params['collection']) ? sanitize_text_field((string) $params['collection']) : '';
    $limit = isset($params['limit']) ? max(1, (int) $params['limit']) : (int) (harbor_printshop_launch_contract()['default_limit'] ?? 12);

    $filtered = array_values(array_filter($items, function (array $item) use ($department, $collection): bool {
        if ($department !== '' && $item['department'] !== $department) {
            return false;
        }
        if ($collection !== '' && $item['collection'] !== $collection) {
            return false;
        }
        return true;
    }));

    return array_slice($filtered, 0, $limit);
}

function harbor_printshop_enabled_gateway_ids(): array
{
    $policy = harbor_printshop_checkout_policy();
    $enabled = array_map('trim', explode(',', (string) ($policy['enable_gateways'] ?? '')));
    return array_values(array_filter($enabled));
}

function harbor_printshop_gateway_ids_for_variations(string $country, array $variationIds): array
{
    $policy = harbor_printshop_checkout_policy();
    $enabled = harbor_printshop_enabled_gateway_ids();
    $blockedClasses = array_map('trim', explode(',', (string) ($policy['cod_blocked_shipping_classes'] ?? '')));
    $codCountries = array_map('trim', explode(',', (string) ($policy['cod_scope_countries'] ?? '')));
    $subtotalLimit = (float) ($policy['cod_subtotal_limit'] ?? 0);
    $subtotal = 0.0;
    $hasBlockedClass = false;

    foreach ($variationIds as $variationId) {
        $variation = wc_get_product((int) $variationId);
        if (!$variation instanceof WC_Product_Variation) {
            continue;
        }
        $subtotal += (float) $variation->get_price();
        if (in_array($variation->get_shipping_class(), $blockedClasses, true)) {
            $hasBlockedClass = true;
        }
    }

    $result = [];
    foreach ($enabled as $gatewayId) {
        if ($gatewayId !== 'cod') {
            $result[] = $gatewayId;
            continue;
        }

        $codAllowed = in_array($country, $codCountries, true) && !$hasBlockedClass && $subtotal <= $subtotalLimit;
        if ($codAllowed) {
            $result[] = 'cod';
        }
    }

    return $result;
}

function harbor_printshop_gateway_ids_for_cart_context(string $country, float $subtotal, array $shippingClasses): array
{
    $policy = harbor_printshop_checkout_policy();
    $enabled = harbor_printshop_enabled_gateway_ids();
    $blockedClasses = array_map('trim', explode(',', (string) ($policy['cod_blocked_shipping_classes'] ?? '')));
    $codCountries = array_map('trim', explode(',', (string) ($policy['cod_scope_countries'] ?? '')));
    $subtotalLimit = (float) ($policy['cod_subtotal_limit'] ?? 0);
    $hasBlockedClass = false;

    foreach ($shippingClasses as $shippingClass) {
        if (in_array((string) $shippingClass, $blockedClasses, true)) {
            $hasBlockedClass = true;
            break;
        }
    }

    $result = [];
    foreach ($enabled as $gatewayId) {
        if ($gatewayId !== 'cod') {
            $result[] = $gatewayId;
            continue;
        }

        $codAllowed = in_array($country, $codCountries, true) && !$hasBlockedClass && $subtotal <= $subtotalLimit;
        if ($codAllowed) {
            $result[] = 'cod';
        }
    }

    return $result;
}

function harbor_printshop_apply_payment_gateway_filter(array $gateways): array
{
    $enabled = harbor_printshop_enabled_gateway_ids();
    foreach (array_keys($gateways) as $gatewayId) {
        if (!in_array($gatewayId, $enabled, true)) {
            unset($gateways[$gatewayId]);
        }
    }

    $country = '';
    $subtotal = 0.0;
    $shippingClasses = [];
    if (function_exists('WC') && WC()->customer) {
        $country = WC()->customer->get_shipping_country() ?: WC()->customer->get_billing_country();
    }
    if (function_exists('WC') && WC()->cart) {
        if (method_exists(WC()->cart, 'get_subtotal')) {
            $subtotal = (float) WC()->cart->get_subtotal();
        }
        foreach (WC()->cart->get_cart() as $item) {
            $product = $item['data'] ?? null;
            if ($product instanceof WC_Product_Variation) {
                $shippingClasses[] = $product->get_shipping_class();
            } elseif ($product instanceof WC_Product) {
                if (isset($item['variation_id']) && (int) $item['variation_id'] > 0) {
                    $variation = wc_get_product((int) $item['variation_id']);
                    if ($variation instanceof WC_Product_Variation) {
                        $shippingClasses[] = $variation->get_shipping_class();
                        continue;
                    }
                }
                $shippingClasses[] = $product->get_shipping_class();
            } elseif (is_object($product) && method_exists($product, 'get_shipping_class')) {
                $shippingClasses[] = (string) $product->get_shipping_class();
            }
        }
    }

    $allowed = harbor_printshop_gateway_ids_for_cart_context($country, $subtotal, $shippingClasses);
    foreach (array_keys($gateways) as $gatewayId) {
        if (!in_array($gatewayId, $allowed, true)) {
            unset($gateways[$gatewayId]);
        }
    }

    return $gateways;
}
