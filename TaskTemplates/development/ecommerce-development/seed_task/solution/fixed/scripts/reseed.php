<?php

declare(strict_types=1);

ini_set('display_errors', '1');
error_reporting(E_ALL);

if (!defined('WP_DISABLE_FATAL_ERROR_HANDLER')) {
    define('WP_DISABLE_FATAL_ERROR_HANDLER', true);
}

require_once '/var/www/html/wp-load.php';
require_once '/var/www/html/wp-admin/includes/taxonomy.php';
require_once '/var/www/html/wp-admin/includes/user.php';
require_once '/var/www/html/wp-content/plugins/harbor-printshop/includes.php';

function harbor_printshop_delete_existing_products(): void
{
    $posts = get_posts([
        'post_type' => ['product', 'product_variation'],
        'post_status' => ['publish', 'draft', 'pending', 'private', 'trash'],
        'numberposts' => -1,
        'fields' => 'ids',
    ]);

    foreach ($posts as $postId) {
        wp_delete_post((int) $postId, true);
    }
}

function harbor_printshop_ensure_users(): void
{
    foreach (harbor_printshop_seed_users() as $userConfig) {
        $existing = get_user_by('email', $userConfig['email']);
        if ($existing instanceof WP_User) {
            wp_update_user([
                'ID' => $existing->ID,
                'role' => $userConfig['role'],
                'user_pass' => $userConfig['password'],
            ]);
            continue;
        }

        $userId = wp_create_user($userConfig['username'], $userConfig['password'], $userConfig['email']);
        if (!is_wp_error($userId)) {
            $user = new WP_User((int) $userId);
            $user->set_role($userConfig['role']);
        }
    }
}

function harbor_printshop_reset_categories(): void
{
    $terms = get_terms([
        'taxonomy' => 'product_cat',
        'hide_empty' => false,
    ]);

    foreach ($terms as $term) {
        if (in_array($term->slug, ['uncategorized'], true)) {
            continue;
        }
        wp_delete_term((int) $term->term_id, 'product_cat');
    }
}

function harbor_printshop_ensure_attribute_taxonomy(): array
{
    $plan = harbor_printshop_collection_plan();
    $name = $plan['size_attribute']['name'];
    $slug = $plan['size_attribute']['slug'];
    $taxonomy = 'pa_' . $slug;
    $attributeId = wc_attribute_taxonomy_id_by_name($slug);

    if (!$attributeId) {
        $attributeId = wc_create_attribute([
            'name' => $name,
            'slug' => $slug,
            'type' => 'select',
            'order_by' => 'menu_order',
            'has_archives' => false,
        ]);
    }

    if (!taxonomy_exists($taxonomy)) {
        register_taxonomy($taxonomy, ['product'], [
            'hierarchical' => false,
            'label' => $name,
            'query_var' => true,
            'rewrite' => false,
        ]);
    }

    $termIds = [];
    $termSlugs = [];
    foreach ($plan['size_attribute']['options'] as $option) {
        $existing = term_exists($option['label'], $taxonomy);
        if (!$existing) {
            $created = wp_insert_term($option['label'], $taxonomy);
            $termId = (int) $created['term_id'];
            $term = get_term($termId, $taxonomy);
        } else {
            $termId = (int) $existing['term_id'];
            $term = get_term($termId, $taxonomy);
        }
        $termIds[] = $termId;
        $termSlugs[$option['key']] = $term ? $term->slug : sanitize_title($option['label']);
    }

    return [
        'attribute_id' => (int) $attributeId,
        'taxonomy' => $taxonomy,
        'term_ids' => $termIds,
        'term_slugs' => $termSlugs,
    ];
}

function harbor_printshop_upsert_term(string $taxonomy, string $slug, string $name): int
{
    $existing = get_term_by('slug', $slug, $taxonomy);
    if ($existing instanceof WP_Term) {
        wp_update_term($existing->term_id, $taxonomy, ['name' => $name]);
        return (int) $existing->term_id;
    }

    $created = wp_insert_term($name, $taxonomy, ['slug' => $slug]);
    return (int) $created['term_id'];
}

function harbor_printshop_ensure_shipping_classes(array $rules): array
{
    $map = [];
    foreach ($rules['shipping_classes'] as $classConfig) {
        $termId = harbor_printshop_upsert_term('product_shipping_class', $classConfig['slug'], $classConfig['name']);
        $map[$classConfig['slug']] = $termId;
    }
    return $map;
}

function harbor_printshop_reset_shipping_zones(): void
{
    foreach (WC_Shipping_Zones::get_zones() as $zoneData) {
        $zone = new WC_Shipping_Zone((int) $zoneData['id']);
        $zone->delete();
    }
}

function harbor_printshop_configure_shipping(array $shippingClassMap): int
{
    $rules = harbor_printshop_shipping_rules();
    harbor_printshop_reset_shipping_zones();

    foreach ($rules['zones'] as $zoneConfig) {
        $zone = new WC_Shipping_Zone();
        $zone->set_zone_name($zoneConfig['name']);
        $zone->set_zone_order((int) $zoneConfig['order']);
        $zoneId = $zone->save();

        $zone = new WC_Shipping_Zone($zoneId);
        foreach ($zoneConfig['locations'] as $location) {
            $zone->add_location($location['code'], $location['type']);
        }
        $zone->save();

        $instanceId = $zone->add_shipping_method($zoneConfig['method']['id']);
        $method = WC_Shipping_Zones::get_shipping_method($instanceId);
        $settings = get_option('woocommerce_flat_rate_' . $instanceId . '_settings', []);
        $settings['enabled'] = 'yes';
        $settings['title'] = $zoneConfig['method']['title'];
        $settings['cost'] = $zoneConfig['method']['base_cost'];
        foreach ($zoneConfig['method']['class_costs'] as $slug => $cost) {
            if (!isset($shippingClassMap[$slug])) {
                continue;
            }
            $settings['class_cost_' . $shippingClassMap[$slug]] = $cost;
        }
        update_option('woocommerce_flat_rate_' . $instanceId . '_settings', $settings);
    }

    return count($rules['zones']);
}

function harbor_printshop_configure_gateways(): int
{
    $enabled = harbor_printshop_enabled_gateway_ids();
    $optionIds = ['bacs', 'cod', 'cheque'];

    foreach ($optionIds as $gatewayId) {
        $settings = get_option('woocommerce_' . $gatewayId . '_settings', []);
        $settings['enabled'] = in_array($gatewayId, $enabled, true) ? 'yes' : 'no';
        update_option('woocommerce_' . $gatewayId . '_settings', $settings);
    }

    return count($enabled);
}

function harbor_printshop_build_product_categories(array $model): array
{
    $departmentIds = [];
    $collectionIds = [];
    foreach ($model as $row) {
        $departmentIds[$row['department_slug']] = harbor_printshop_upsert_term(
            'product_cat',
            $row['department_slug'],
            $row['department_name']
        );
        $collectionIds[$row['collection_key']] = harbor_printshop_upsert_term(
            'product_cat',
            $row['collection_key'],
            $row['collection_title']
        );
    }

    return [
        'departments' => $departmentIds,
        'collections' => $collectionIds,
    ];
}

function harbor_printshop_create_products(array $model, array $categoryIds, array $attributeMeta, array $shippingClassMap): array
{
    $productIds = [];
    $variationIds = [];

    foreach ($model as $row) {
        $product = new WC_Product_Variable();
        $product->set_name($row['merchandising_title']);
        $product->set_slug($row['slug']);
        $product->set_status($row['launch_state'] === 'publish' ? 'publish' : 'draft');
        $product->set_catalog_visibility('visible');
        $product->set_description((string) ($row['detail']['title'] ?? ''));
        $product->set_short_description((string) ($row['detail']['artistDisplayName'] ?? ''));
        $product->set_category_ids([
            $categoryIds['departments'][$row['department_slug']],
            $categoryIds['collections'][$row['collection_key']],
        ]);

        $attribute = new WC_Product_Attribute();
        $attribute->set_id($attributeMeta['attribute_id']);
        $attribute->set_name($attributeMeta['taxonomy']);
        $attribute->set_options($attributeMeta['term_ids']);
        $attribute->set_visible(true);
        $attribute->set_variation(true);
        $product->set_attributes([$attribute]);
        $product->set_default_attributes([
            $attributeMeta['taxonomy'] => $attributeMeta['term_slugs']['small'],
        ]);

        $product->update_meta_data('harbor_object_id', $row['object_id']);
        $product->update_meta_data('harbor_artist_name', $row['detail']['artistDisplayName'] ?? '');
        $product->update_meta_data('harbor_department_slug', $row['department_slug']);
        $product->update_meta_data('harbor_department_name', $row['department_name']);
        $product->update_meta_data('harbor_collection_key', $row['collection_key']);
        $product->update_meta_data('harbor_collection_title', $row['collection_title']);
        $product->update_meta_data('harbor_collection_sort_order', $row['collection_sort_order']);
        $product->update_meta_data('harbor_featured_rank', $row['featured_rank']);
        $product->update_meta_data('harbor_public_domain_clearance', $row['public_domain_clearance'] ? 'true' : 'false');
        $product->update_meta_data('harbor_launch_state', $row['launch_state']);
        $product->update_meta_data('harbor_primary_image', (string) ($row['detail']['primaryImageSmall'] ?? ''));
        $product->update_meta_data('harbor_object_url', (string) ($row['detail']['objectURL'] ?? ''));
        $product->update_meta_data('harbor_object_date', (string) ($row['detail']['objectDate'] ?? ''));
        $productId = $product->save();
        $productIds[] = $productId;

        wp_set_object_terms(
            $productId,
            array_map(static fn(array $option): string => $option['label'], harbor_printshop_size_options()),
            $attributeMeta['taxonomy']
        );

        foreach ($row['variations'] as $variationRow) {
            $variation = new WC_Product_Variation();
            $variation->set_parent_id($productId);
            $variation->set_regular_price((string) $variationRow['price']);
            $variation->set_price((string) $variationRow['price']);
            $variation->set_manage_stock(true);
            $variation->set_stock_quantity($variationRow['stock']);
            $variation->set_stock_status($variationRow['stock'] > 0 ? 'instock' : 'outofstock');
            $variation->set_sku($variationRow['sku']);
            $variation->set_shipping_class_id($shippingClassMap[$variationRow['shipping_class']] ?? 0);
            $variation->set_attributes([
                $attributeMeta['taxonomy'] => $attributeMeta['term_slugs'][$variationRow['key']],
            ]);
            $variation->update_meta_data('harbor_size_key', $variationRow['key']);
            $variationId = $variation->save();
            $variationIds[] = $variationId;
        }
    }

    return [
        'product_ids' => $productIds,
        'variation_ids' => $variationIds,
    ];
}

function harbor_printshop_write_summary(array $summary): void
{
    $outputDir = '/app/workspace/output';
    if (!is_dir($outputDir)) {
        mkdir($outputDir, 0777, true);
    }
    file_put_contents(
        $outputDir . '/seed-summary.json',
        json_encode($summary, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL
    );
}

harbor_printshop_ensure_users();
harbor_printshop_delete_existing_products();
harbor_printshop_reset_categories();

$model = harbor_printshop_build_seed_model();
$categoryIds = harbor_printshop_build_product_categories($model);
$attributeMeta = harbor_printshop_ensure_attribute_taxonomy();
$shippingClassMap = harbor_printshop_ensure_shipping_classes(harbor_printshop_shipping_rules());
$shippingZones = harbor_printshop_configure_shipping($shippingClassMap);
$paymentGateways = harbor_printshop_configure_gateways();
$created = harbor_printshop_create_products($model, $categoryIds, $attributeMeta, $shippingClassMap);
$launchFeedCount = count(harbor_printshop_build_launch_feed_items(false));

$summary = [
    'products' => count($created['product_ids']),
    'variableProducts' => count($created['product_ids']),
    'variations' => count($created['variation_ids']),
    'departments' => count($categoryIds['departments']),
    'collections' => count($categoryIds['collections']),
    'shippingZones' => $shippingZones,
    'paymentGateways' => $paymentGateways,
    'launchFeedCount' => $launchFeedCount,
];

harbor_printshop_write_summary($summary);
fwrite(STDOUT, "reseed complete\n");
