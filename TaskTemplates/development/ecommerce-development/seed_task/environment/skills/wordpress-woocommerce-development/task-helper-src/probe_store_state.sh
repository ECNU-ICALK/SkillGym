#!/bin/bash
set -euo pipefail

bash /opt/bootstrap/start_stack.sh >/tmp/harbor-skill-probe.log 2>&1

wp eval '
$products = wc_get_products([
    "limit" => -1,
    "status" => ["publish", "draft", "private"],
    "return" => "ids",
]);
$variable = 0;
$variations = 0;
foreach ($products as $product_id) {
    $product = wc_get_product($product_id);
    if ($product && $product->is_type("variable")) {
        $variable++;
        $variations += count($product->get_children());
    }
}
$classes = [];
foreach (WC()->shipping()->get_shipping_classes() as $class) {
    $classes[] = $class->slug;
}
$enabled = [];
foreach (WC()->payment_gateways()->payment_gateways() as $id => $gateway) {
    if ($gateway->enabled === "yes") {
        $enabled[] = $id;
    }
}

class HarborProbeProduct extends WC_Product_Simple {
    public function __construct(string $shippingClass) {
        parent::__construct();
        $term = get_term_by("slug", $shippingClass, "product_shipping_class");
        if ($term instanceof WP_Term) {
            $this->set_shipping_class_id((int) $term->term_id);
        }
    }
}

class HarborProbeCart extends WC_Cart {
    private float $subtotal;
    private array $items;

    public function __construct(float $subtotal, array $shippingClasses) {
        $this->subtotal = $subtotal;
        $this->items = [];
        $lineTotal = count($shippingClasses) > 0 ? $subtotal / count($shippingClasses) : $subtotal;
        foreach ($shippingClasses as $idx => $shippingClass) {
            $variationId = harbor_probe_variation_id_for_shipping_class($shippingClass);
            $variation = $variationId > 0 ? wc_get_product($variationId) : new HarborProbeProduct($shippingClass);
            $productId = $variation instanceof WC_Product_Variation ? $variation->get_parent_id() : 0;
            $this->items[] = [
                "key" => "i" . $idx,
                "product_id" => $productId,
                "variation_id" => $variationId,
                "data" => $variation,
                "quantity" => 1,
                "line_total" => $lineTotal,
                "line_subtotal" => $lineTotal,
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

    public function get_total($context = "view") {
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
            "contents" => $this->items,
            "contents_cost" => $this->subtotal,
            "applied_coupons" => [],
            "user" => ["ID" => 0],
            "destination" => [
                "country" => WC()->customer ? WC()->customer->get_shipping_country() : "",
                "state" => WC()->customer ? WC()->customer->get_shipping_state() : "",
                "postcode" => WC()->customer ? WC()->customer->get_shipping_postcode() : "",
                "city" => WC()->customer ? WC()->customer->get_shipping_city() : "",
                "address" => WC()->customer ? WC()->customer->get_shipping_address() : "",
                "address_1" => WC()->customer ? WC()->customer->get_shipping_address() : "",
                "address_2" => WC()->customer ? WC()->customer->get_shipping_address_2() : "",
            ],
        ]];
    }
}

function harbor_probe_variation_id_for_shipping_class(string $shippingClass): int {
    $variationIds = get_posts([
        "post_type" => "product_variation",
        "post_status" => ["publish", "private"],
        "numberposts" => -1,
        "fields" => "ids",
    ]);
    foreach ($variationIds as $variationId) {
        $variation = wc_get_product($variationId);
        if ($variation instanceof WC_Product_Variation && $variation->get_shipping_class() === $shippingClass) {
            return (int) $variationId;
        }
    }
    return 0;
}

function harbor_probe_available_gateways(string $country, float $subtotal, array $shippingClasses): array {
    WC()->customer = new WC_Customer(0, true);
    WC()->customer->set_shipping_country($country);
    WC()->cart = new HarborProbeCart($subtotal, $shippingClasses);
    $gateways = WC()->payment_gateways()->payment_gateways();
    $available = apply_filters("woocommerce_available_payment_gateways", $gateways);
    return array_keys($available);
}

echo json_encode([
    "products" => count($products),
    "variableProducts" => $variable,
    "variations" => $variations,
    "shippingClasses" => $classes,
    "shippingZones" => array_map(
        static fn($zone) => $zone["zone_name"],
        array_values(WC_Shipping_Zones::get_zones())
    ),
    "enabledGateways" => $enabled,
    "gatewayScenarios" => [
        "us_standard_120" => harbor_probe_available_gateways("US", 120.0, ["standard-print"]),
        "us_oversized_120" => harbor_probe_available_gateways("US", 120.0, ["oversized-print"]),
        "us_standard_200" => harbor_probe_available_gateways("US", 200.0, ["standard-print"]),
        "ca_standard_120" => harbor_probe_available_gateways("CA", 120.0, ["standard-print"]),
    ],
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
' --allow-root --path=/var/www/html
