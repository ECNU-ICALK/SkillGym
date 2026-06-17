<?php
/**
 * Plugin Name: Harbor Printshop
 * Description: Workspace plugin for the museum printshop task.
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

require_once __DIR__ . '/includes.php';

add_filter('woocommerce_available_payment_gateways', function (array $gateways): array {
    return harbor_printshop_apply_payment_gateway_filter($gateways);
}, 20);

add_action('rest_api_init', function (): void {
    register_rest_route('harbor-printshop/v1', '/launch-feed', [
        'methods' => 'GET',
        'permission_callback' => '__return_true',
        'callback' => function (WP_REST_Request $request): WP_REST_Response {
            $inStockOnly = harbor_printshop_parse_bool($request->get_param('in_stock_only'));
            $allItems = harbor_printshop_build_launch_feed_items($inStockOnly);
            $items = harbor_printshop_filter_feed_items($allItems, $request->get_params());
            return new WP_REST_Response([
                'items' => $items,
                'total' => count($allItems),
            ], 200);
        },
    ]);
});
