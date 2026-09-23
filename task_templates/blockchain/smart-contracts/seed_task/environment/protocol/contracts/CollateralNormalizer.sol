// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

library CollateralNormalizer {
    function scaleToWad(uint256 assets, uint8 assetDecimals) internal pure returns (uint256) {
        if (assetDecimals == 18) {
            return assets;
        }
        if (assetDecimals < 18) {
            return assets * (10 ** (18 - assetDecimals));
        }
        return assets / (10 ** (assetDecimals - 18));
    }
}
