#!/bin/bash
set -euo pipefail

WP_PATH="${WP_ROOT:-/var/www/html}"

echo "[plugins]"
wp plugin list --allow-root --path="$WP_PATH"
echo
echo "[products]"
wp post list --allow-root --path="$WP_PATH" --post_type=product --fields=ID,post_name,post_status,post_title
echo
echo "[shipping_classes]"
wp eval --allow-root --path="$WP_PATH" 'print_r(WC()->shipping()->get_shipping_classes());'
echo
echo "[shipping_zones]"
wp eval --allow-root --path="$WP_PATH" 'foreach (WC_Shipping_Zones::get_zones() as $zone) { echo $zone["zone_name"] . PHP_EOL; foreach ($zone["shipping_methods"] as $method) { echo "  - " . $method->get_method_title() . " cost=" . $method->get_option("cost") . PHP_EOL; }}'
echo
echo "[gateways]"
wp eval --allow-root --path="$WP_PATH" '$gateways = WC()->payment_gateways()->payment_gateways(); foreach ($gateways as $id => $gateway) { echo $id . " enabled=" . $gateway->enabled . PHP_EOL; }'
