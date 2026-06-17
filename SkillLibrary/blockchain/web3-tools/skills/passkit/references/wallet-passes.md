# PassKit Extended Patterns

Overflow reference for the `passkit` skill. Contains advanced patterns that exceed the main skill file's scope.

## Contents

- [Recurring Payment Requests](#recurring-payment-requests)
- [Coupon Code Support](#coupon-code-support)
- [Multi-Merchant Payments](#multi-merchant-payments)
- [Deferred Payments](#deferred-payments)
- [Updating Passes with Push Notifications](#updating-passes-with-push-notifications)
- [SwiftUI Payment Flow](#swiftui-payment-flow)

## Recurring Payment Requests

Set up subscription-style recurring payments with `PKRecurringPaymentRequest`.

```swift
import PassKit

func createSubscriptionRequest() -> PKPaymentRequest {
    let request = PKPaymentRequest()
    request.merchantIdentifier = "merchant.com.example.app"
    request.countryCode = "US"
    request.currencyCode = "USD"
    request.supportedNetworks = [.visa, .masterCard, .amex]
    request.merchantCapabilities = .threeDSecure

    let monthlyItem = PKRecurringPaymentSummaryItem(
        label: "Monthly Subscription",
        amount: 9.99
    )
    monthlyItem.intervalUnit = .month
    monthlyItem.intervalCount = 1

    request.paymentSummaryItems = [
        monthlyItem,
        PKPaymentSummaryItem(label: "My Service", amount: 9.99)
    ]

    let recurringRequest = PKRecurringPaymentRequest(
        paymentDescription: "Monthly Premium",
        regularBilling: monthlyItem,
        managementURL: URL(string: "https://example.com/manage")!
    )
    recurringRequest.billingAgreement = "You will be charged $9.99/month."
    request.recurringPaymentRequest = recurringRequest

    return request
}
```

## Coupon Code Support

Enable coupon codes on the payment sheet and handle validation.

```swift
func createRequestWithCoupons() -> PKPaymentRequest {
    let request = createPaymentRequest()
    request.supportsCouponCode = true
    request.couponCode = "" // pre-fill if known
    return request
}

// Handle coupon code entry in the delegate
extension PaymentCoordinator: PKPaymentAuthorizationControllerDelegate {
    func paymentAuthorizationController(
        _ controller: PKPaymentAuthorizationController,
        didChangeCouponCode couponCode: String,
        handler completion: @escaping (PKPaymentRequestCouponCodeUpdate) -> Void
    ) {
        Task {
            do {
                let discount = try await validateCoupon(couponCode)
                let updatedItems = applyDiscount(discount)
                completion(PKPaymentRequestCouponCodeUpdate(
                    paymentSummaryItems: updatedItems
                ))
            } catch {
                let couponError = PKPaymentRequest.paymentCouponCodeInvalidError(
                    localizedDescription: "Invalid coupon code."
                )
                completion(PKPaymentRequestCouponCodeUpdate(
                    errors: [couponError],
                    paymentSummaryItems: originalItems
                ))
            }
        }
    }
}
```

## Multi-Merchant Payments

Request separate payment tokens for multiple merchants in one transaction using `PKPaymentTokenContext`.

```swift
func createMultiMerchantRequest() -> PKPaymentRequest {
    let request = PKPaymentRequest()
    request.merchantIdentifier = "merchant.com.example.platform"
    request.countryCode = "US"
    request.currencyCode = "USD"
    request.supportedNetworks = [.visa, .masterCard, .amex]
    request.merchantCapabilities = .threeDSecure

    request.paymentSummaryItems = [
        PKPaymentSummaryItem(label: "Hotel Stay", amount: 299.00),
        PKPaymentSummaryItem(label: "Car Rental", amount: 89.00),
        PKPaymentSummaryItem(label: "Travel Platform", amount: 388.00)
    ]

    let hotelContext = PKPaymentTokenContext(
        merchantIdentifier: "merchant.com.example.hotel",
        externalIdentifier: "hotel-booking-123",
        merchantName: "Example Hotel",
        merchantDomain: "hotel.example.com",
        amount: 299.00
    )

    let carContext = PKPaymentTokenContext(
        merchantIdentifier: "merchant.com.example.carrental",
        externalIdentifier: "car-rental-456",
        merchantName: "Example Car Rental",
        merchantDomain: "carrental.example.com",
        amount: 89.00
    )

    request.multiTokenContexts = [hotelContext, carContext]
    return request
}
```

## Deferred Payments

Set up payments that charge later, such as hotel bookings or pre-orders.

```swift
func createDeferredPaymentRequest() -> PKPaymentRequest {
    let request = createPaymentRequest()

    let deferredDate = Calendar.current.date(
        byAdding: .day, value: 14, to: Date()
    )!

    let deferredRequest = PKDeferredPaymentRequest(
        paymentDescription: "Hotel Booking - Check-in",
        deferredBilling: PKDeferredPaymentSummaryItem(
            label: "Hotel Stay (charged at check-in)",
            amount: 299.00
        ),
        managementURL: URL(string: "https://example.com/bookings")!
    )
    deferredRequest.freeCancellationDate = deferredDate
    deferredRequest.freeCancellationDateTimeZone = .current

    request.deferredPaymentRequest = deferredRequest
    return request
}
```

## Updating Passes with Push Notifications

Passes in Wallet can receive push notifications to trigger an update. The flow:

1. The pass JSON includes a `webServiceURL` and `authenticationToken`
2. When the pass is added to Wallet, the device registers with your server
3. To update, send an empty push notification to the device
4. The device calls your `webServiceURL` to fetch the updated `.pkpass` bundle

### Server Endpoints (your web service must implement)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/devices/{deviceId}/registrations/{passTypeId}/{serialNumber}` | Register device for updates |
| DELETE | `/v1/devices/{deviceId}/registrations/{passTypeId}/{serialNumber}` | Unregister device |
| GET | `/v1/devices/{deviceId}/registrations/{passTypeId}` | Get serial numbers of updated passes |
| GET | `/v1/passes/{passTypeId}/{serialNumber}` | Download the latest pass |

### Checking for Updates In-App

```swift
import PassKit

let library = PKPassLibrary()

// Replace an existing pass with updated data
func updatePass(newPassData: Data) {
    guard let updatedPass = try? PKPass(data: newPassData) else { return }
    if library.containsPass(updatedPass) {
        library.replacePass(with: updatedPass)
    }
}
```

## SwiftUI Payment Flow

A complete SwiftUI payment view with availability check, button, and processing.

```swift
import SwiftUI
import PassKit

struct PaymentView: View {
    @State private var paymentStatus: PaymentStatus = .idle

    private var canPay: Bool {
        PKPaymentAuthorizationController.canMakePayments(
            usingNetworks: [.visa, .masterCard, .amex],
            capabilities: .threeDSecure
        )
    }

    var body: some View {
        VStack {
            OrderSummaryView()

            if canPay {
                PayWithApplePayButton(.buy) {
                    processPayment()
                }
                .payWithApplePayButtonStyle(.black)
                .frame(height: 48)
            } else {
                Button("Checkout with Card") {
                    // Fallback payment flow
                }
                .buttonStyle(.borderedProminent)
            }

            if case .error(let message) = paymentStatus {
                Text(message)
                    .foregroundStyle(.red)
                    .font(.caption)
            }
        }
        .padding()
    }

    @MainActor
    private func processPayment() {
        let coordinator = PaymentCoordinator { result in
            paymentStatus = result
        }
        coordinator.startPayment()
    }
}

enum PaymentStatus {
    case idle
    case processing
    case success
    case error(String)
}
```
