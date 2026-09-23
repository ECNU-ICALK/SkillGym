// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {ApprovalHelper} from "./ApprovalHelper.sol";
import {CollateralNormalizer} from "./CollateralNormalizer.sol";
import {CollateralRegistry} from "./CollateralRegistry.sol";

contract CollateralVault is ReentrancyGuard {
    using SafeERC20 for IERC20;
    using ApprovalHelper for IERC20;

    CollateralRegistry public immutable registry;
    mapping(address => uint256) public sharesByAccount;
    mapping(address => uint256) public totalManagedAssets;

    constructor(CollateralRegistry registry_) {
        registry = registry_;
    }

    function deposit(address token, uint256 assets, address receiver) external nonReentrant returns (uint256 mintedShares) {
        require(registry.allowedCollateral(token), "token-not-allowed");

        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        IERC20(token).safeTransferFrom(msg.sender, address(this), assets);
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));
        uint256 receivedAssets = balanceAfter - balanceBefore;

        mintedShares = CollateralNormalizer.scaleToWad(receivedAssets, registry.collateralDecimals(token));
        sharesByAccount[receiver] += mintedShares;
        totalManagedAssets[token] += receivedAssets;
    }

    function approveSpender(address token, address spender, uint256 amount) external nonReentrant {
        IERC20(token).resetAndApprove(spender, amount);
    }

    function previewDeposit(address token, uint256 assets) external view returns (uint256 previewShares) {
        previewShares = CollateralNormalizer.scaleToWad(assets, registry.collateralDecimals(token));
    }
}
