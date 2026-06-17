// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CollateralRegistry {
    mapping(address => bool) public allowedCollateral;
    mapping(address => uint8) public collateralDecimals;

    event CollateralAdded(address indexed token, uint8 decimals);
    event CollateralRemoved(address indexed token);

    function setCollateral(address token, uint8 decimals_, bool allowed) external {
        collateralDecimals[token] = decimals_;
        allowedCollateral[token] = allowed;
        if (allowed) {
            emit CollateralAdded(token, decimals_);
        } else {
            emit CollateralRemoved(token);
        }
    }
}
