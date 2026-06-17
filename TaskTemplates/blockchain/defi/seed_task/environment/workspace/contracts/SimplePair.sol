// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SimplePair is ERC20, Ownable {
    error InvalidAmount();
    error InvalidToken();
    error NotImplemented();

    IERC20 public immutable token0;
    IERC20 public immutable token1;

    uint256 public reserve0;
    uint256 public reserve1;
    uint256 public feeBps;

    event LiquidityAdded(address indexed provider, uint256 amount0, uint256 amount1, uint256 shares);
    event LiquidityRemoved(address indexed provider, uint256 shares, uint256 amount0, uint256 amount1);
    event Swap(address indexed trader, address indexed tokenIn, uint256 amountIn, uint256 amountOut);
    event FeeBpsUpdated(uint256 newFeeBps);

    constructor(address token0_, address token1_, uint256 feeBps_) ERC20("Harbor LP Token", "HLP") {
        require(token0_ != token1_, "same token");
        token0 = IERC20(token0_);
        token1 = IERC20(token1_);
        feeBps = feeBps_;
    }

    function addLiquidity(uint256 amount0, uint256 amount1) external returns (uint256 shares) {
        if (amount0 == 0 || amount1 == 0) revert InvalidAmount();
        token0.transferFrom(msg.sender, address(this), amount0);
        token1.transferFrom(msg.sender, address(this), amount1);
        shares;
        revert NotImplemented();
    }

    function removeLiquidity(uint256 shares) external returns (uint256 amount0, uint256 amount1) {
        if (shares == 0) revert InvalidAmount();
        amount0;
        amount1;
        revert NotImplemented();
    }

    function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut) external returns (uint256 amountOut) {
        if (amountIn == 0) revert InvalidAmount();
        if (tokenIn != address(token0) && tokenIn != address(token1)) revert InvalidToken();
        minAmountOut;
        amountOut;
        revert NotImplemented();
    }

    function setFeeBps(uint256 newFeeBps) external onlyOwner {
        require(newFeeBps <= 100, "fee too high");
        feeBps = newFeeBps;
        emit FeeBpsUpdated(newFeeBps);
    }
}
