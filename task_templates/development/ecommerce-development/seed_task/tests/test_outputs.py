from __future__ import annotations

import json
import os
import time
from pathlib import Path

from oracle import (
    BASE_URL,
    REQUIRED_FEED_FIELDS,
    WORKSPACE_ROOT,
    expected_launch_items,
    expected_launch_rows,
    expected_summary,
    extract_feed_items,
    request_json,
    simple_slug,
    wp_eval_json,
)


SUMMARY_PATH = WORKSPACE_ROOT / "output" / "seed-summary.json"


def wait_for_site() -> None:
    for _ in range(120):
        status, _payload = request_json("/wp-json/")
        if status == 200:
            return
        time.sleep(1)
    raise RuntimeError(f"site did not become ready at {BASE_URL}")


def assert_summary() -> None:
    if not SUMMARY_PATH.exists():
        raise AssertionError("missing /app/workspace/output/seed-summary.json")
    actual = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected = expected_summary()
    missing = [key for key in expected if key not in actual]
    if missing:
        raise AssertionError(f"summary missing keys: {missing}")
    mismatches = {key: (actual[key], expected[key]) for key in expected if int(actual[key]) != int(expected[key])}
    if mismatches:
        raise AssertionError(f"summary value mismatch: {mismatches}")


def assert_catalog_import() -> None:
    stats = wp_eval_json(
        r"""
        $products = wc_get_products([
            'limit' => -1,
            'status' => ['publish', 'draft', 'private'],
            'return' => 'ids',
        ]);
        $variable = 0;
        $variations = 0;
        foreach ($products as $product_id) {
            $product = wc_get_product($product_id);
            if (!$product) { continue; }
            if ($product->is_type('variable')) {
                $variable += 1;
                $variations += count($product->get_children());
            }
        }
        echo json_encode([
            'products' => count($products),
            'variableProducts' => $variable,
            'variations' => $variations,
        ]);
        """
    )
    expected = expected_summary()
    for key in ("products", "variableProducts", "variations"):
        if int(stats[key]) != int(expected[key]):
            raise AssertionError(f"{key} mismatch: got={stats[key]} expected={expected[key]}")


def assert_launch_feed() -> None:
    expected_rows = expected_launch_rows()
    expected_items = expected_launch_items()
    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed")
    if status != 200:
        raise AssertionError(f"launch-feed unavailable: status={status} payload={payload}")

    items = extract_feed_items(payload)
    if len(items) != len(expected_rows):
        raise AssertionError(f"launch-feed count mismatch: got={len(items)} expected={len(expected_rows)}")

    for idx, item in enumerate(items):
        missing = REQUIRED_FEED_FIELDS - set(item.keys())
        if missing:
            raise AssertionError(f"feed item[{idx}] missing required fields: {sorted(missing)}")
        if not isinstance(item["title"], str) or not item["title"].strip():
            raise AssertionError(f"feed item[{idx}] has empty title")
        if not isinstance(item["slug"], str) or not item["slug"].strip():
            raise AssertionError(f"feed item[{idx}] has empty slug")
        if not isinstance(item["collection"], str) or not item["collection"].strip():
            raise AssertionError(f"feed item[{idx}] has empty collection")
        if not isinstance(item["department"], str) or not item["department"].strip():
            raise AssertionError(f"feed item[{idx}] has empty department")
        try:
            float(item["price"])
        except Exception as exc:
            raise AssertionError(f"feed item[{idx}] price is not numeric: {item['price']} ({exc})") from exc

        expected_item = expected_items[idx]
        for key in ("productId", "title", "artistName", "department", "collection", "sku", "availability"):
            if item.get(key) != expected_item[key]:
                raise AssertionError(
                    f"feed item[{idx}] {key} mismatch: got={item.get(key)!r} expected={expected_item[key]!r}"
                )
        allowed_slugs = {expected_item["slug"], simple_slug(str(expected_item["title"]))}
        if item.get("slug") not in allowed_slugs:
            raise AssertionError(
                f"feed item[{idx}] slug mismatch: got={item.get('slug')!r} expected one of={sorted(allowed_slugs)!r}"
            )
        if not isinstance(item.get("image"), str) or not item["image"].strip():
            raise AssertionError(f"feed item[{idx}] has empty image")
        if f"{float(item['price']):.2f}" != expected_item["price"]:
            raise AssertionError(
                f"feed item[{idx}] price mismatch: got={float(item['price']):.2f} expected={expected_item['price']}"
            )

    # Filter checks derived from seed data.
    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed?collection=portrait-studio")
    if status != 200:
        raise AssertionError(f"collection filter failed: status={status}")
    portrait_items = extract_feed_items(payload)
    expected_portrait = sum(1 for row in expected_rows if row.collection_key == "portrait-studio")
    if len(portrait_items) != expected_portrait:
        raise AssertionError(f"portrait-studio filter mismatch: got={len(portrait_items)} expected={expected_portrait}")

    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed?department=asian-art")
    if status != 200:
        raise AssertionError(f"department filter failed: status={status}")
    asian_items = extract_feed_items(payload)
    expected_asian = sum(1 for row in expected_rows if row.department_slug == "asian-art")
    if len(asian_items) != expected_asian:
        raise AssertionError(f"asian-art filter mismatch: got={len(asian_items)} expected={expected_asian}")

    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed?limit=2")
    if status != 200:
        raise AssertionError(f"limit filter failed: status={status}")
    if len(extract_feed_items(payload)) != 2:
        raise AssertionError("limit filter expected exactly 2 items")

    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed?in_stock_only=true")
    if status != 200:
        raise AssertionError(f"in_stock_only filter failed: status={status}")
    stock_items = extract_feed_items(payload)
    if len(stock_items) > len(items):
        raise AssertionError("in_stock_only filter cannot return more rows than the default feed")


def assert_shipping_configuration() -> None:
    data = wp_eval_json(
        r"""
        $classes = [];
        foreach (WC()->shipping()->get_shipping_classes() as $class) {
            $classes[$class->slug] = $class->name;
        }
        $zones = [];
        foreach (WC_Shipping_Zones::get_zones() as $zone) {
            $entry = [
                'name' => $zone['zone_name'],
                'locations' => [],
                'methods' => [],
            ];
            foreach ($zone['zone_locations'] as $loc) {
                $entry['locations'][] = ['type' => $loc->type, 'code' => $loc->code];
            }
            foreach ($zone['shipping_methods'] as $method) {
                $entry['methods'][] = [
                    'id' => $method->id,
                    'title' => $method->get_option('title'),
                    'cost' => (string) $method->get_option('cost'),
                ];
            }
            $zones[] = $entry;
        }
        echo json_encode(['classes' => $classes, 'zones' => $zones]);
        """
    )

    classes = data["classes"]
    for required_slug in ("standard-print", "oversized-print"):
        if required_slug not in classes:
            raise AssertionError(f"missing shipping class: {required_slug}")

    zone_names = {zone["name"] for zone in data["zones"]}
    expected_zone_names = {"United States", "Canada", "Europe"}
    if zone_names != expected_zone_names:
        raise AssertionError(f"shipping zones mismatch: got={zone_names} expected={expected_zone_names}")

    method_titles = {
        method["title"]
        for zone in data["zones"]
        for method in zone["methods"]
        if method["id"] == "flat_rate"
    }
    expected_titles = {"Ground Prints", "Tracked Prints", "International Prints"}
    if method_titles != expected_titles:
        raise AssertionError(f"flat-rate titles mismatch: got={method_titles} expected={expected_titles}")


def assert_payment_rules() -> None:
    checks = wp_eval_json(
        r"""
        if (!defined('DOING_AJAX')) {
            define('DOING_AJAX', true);
        }

        class HarborVerifierProduct extends WC_Product_Simple {
            public function __construct(string $shippingClass) {
                parent::__construct();
                $term = get_term_by('slug', $shippingClass, 'product_shipping_class');
                if ($term instanceof WP_Term) {
                    $this->set_shipping_class_id((int) $term->term_id);
                }
            }
        }

        class HarborVerifierCart extends WC_Cart {
            private float $subtotal;
            private array $items;
            public function __construct(float $subtotal, array $shippingClasses) {
                $this->subtotal = $subtotal;
                $this->items = [];
                $lineTotal = count($shippingClasses) > 0 ? $subtotal / count($shippingClasses) : $subtotal;
                foreach ($shippingClasses as $idx => $shippingClass) {
                    $variationId = harbor_verifier_variation_id_for_shipping_class($shippingClass);
                    $variation = $variationId > 0 ? wc_get_product($variationId) : new HarborVerifierProduct($shippingClass);
                    $productId = $variation instanceof WC_Product_Variation ? $variation->get_parent_id() : 0;
                    $this->items[] = [
                        'key' => 'i' . $idx,
                        'product_id' => $productId,
                        'variation_id' => $variationId,
                        'data' => $variation,
                        'quantity' => 1,
                        'line_total' => $lineTotal,
                        'line_subtotal' => $lineTotal,
                    ];
                }
            }
            public function get_subtotal() {
                return $this->subtotal;
            }
            public function get_cart() {
                return $this->items;
            }
            public function get_cart_contents() {
                return $this->items;
            }
            public function get_cart_contents_total() {
                return $this->subtotal;
            }
            public function get_displayed_subtotal() {
                return $this->subtotal;
            }
            public function get_total($context = 'view') {
                return $this->subtotal;
            }
            public function get_fees() {
                return [];
            }
            public function get_coupons($deprecated = null) {
                return [];
            }
            public function get_applied_coupons() {
                return [];
            }
            public function needs_shipping() {
                return !empty($this->items);
            }
            public function is_empty() {
                return empty($this->items);
            }
            public function get_cart_contents_count() {
                return count($this->items);
            }
            public function get_shipping_packages() {
                return [[
                    'contents' => $this->items,
                    'contents_cost' => $this->subtotal,
                    'applied_coupons' => [],
                    'user' => ['ID' => 0],
                    'destination' => [
                        'country' => WC()->customer ? WC()->customer->get_shipping_country() : '',
                        'state' => WC()->customer ? WC()->customer->get_shipping_state() : '',
                        'postcode' => WC()->customer ? WC()->customer->get_shipping_postcode() : '',
                        'city' => WC()->customer ? WC()->customer->get_shipping_city() : '',
                        'address' => WC()->customer ? WC()->customer->get_shipping_address() : '',
                        'address_1' => WC()->customer ? WC()->customer->get_shipping_address() : '',
                        'address_2' => WC()->customer ? WC()->customer->get_shipping_address_2() : '',
                    ],
                ]];
            }
        }

        function harbor_verifier_variation_id_for_shipping_class(string $shippingClass): int {
            $variationIds = get_posts([
                'post_type' => 'product_variation',
                'post_status' => ['publish', 'private'],
                'numberposts' => -1,
                'fields' => 'ids',
            ]);
            foreach ($variationIds as $variationId) {
                $variation = wc_get_product($variationId);
                if ($variation instanceof WC_Product_Variation && $variation->get_shipping_class() === $shippingClass) {
                    return (int) $variationId;
                }
            }
            return 0;
        }

        function harbor_verifier_available_gateways(string $country, float $subtotal, array $shippingClasses): array {
            WC()->customer = new WC_Customer(0, true);
            WC()->customer->set_shipping_country($country);
            WC()->cart = new HarborVerifierCart($subtotal, $shippingClasses);
            $gateways = WC()->payment_gateways()->payment_gateways();
            $available = apply_filters('woocommerce_available_payment_gateways', $gateways);
            return array_keys($available);
        }

        $enabled = [];
        foreach (WC()->payment_gateways()->payment_gateways() as $id => $gateway) {
            if ($gateway->enabled === 'yes') {
                $enabled[] = $id;
            }
        }

        echo json_encode([
            'enabled' => $enabled,
            'us_standard_120' => harbor_verifier_available_gateways('US', 120.0, ['standard-print']),
            'us_oversized_120' => harbor_verifier_available_gateways('US', 120.0, ['oversized-print']),
            'us_standard_200' => harbor_verifier_available_gateways('US', 200.0, ['standard-print']),
            'ca_standard_120' => harbor_verifier_available_gateways('CA', 120.0, ['standard-print']),
        ]);
        """
    )

    enabled = set(checks["enabled"])
    if "bacs" not in enabled or "cod" not in enabled:
        raise AssertionError(f"expected bacs and cod enabled, got enabled={sorted(enabled)}")
    if "cheque" in enabled:
        raise AssertionError("cheque should be disabled")

    us_standard = set(checks["us_standard_120"])
    if "bacs" not in us_standard or "cod" not in us_standard:
        raise AssertionError(f"US standard subtotal=120 should allow bacs+cod, got={sorted(us_standard)}")

    for key in ("us_oversized_120", "us_standard_200", "ca_standard_120"):
        gateway_set = set(checks[key])
        if "bacs" not in gateway_set:
            raise AssertionError(f"{key} should still allow bacs, got={sorted(gateway_set)}")
        if "cod" in gateway_set:
            raise AssertionError(f"{key} should block cod, got={sorted(gateway_set)}")


def main() -> None:
    wait_for_site()
    assert_summary()
    assert_catalog_import()
    assert_launch_feed()
    assert_shipping_configuration()
    assert_payment_rules()
    print("PASS")


if __name__ == "__main__":
    main()
