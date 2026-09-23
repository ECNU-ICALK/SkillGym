// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SimplePair is ERC20, Ownable {
    error InvalidAmount();
    error InvalidToken();
    error SlippageExceeded();

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
        require(feeBps_ <= 100, "fee too high");
        token0 = IERC20(token0_);
        token1 = IERC20(token1_);
        feeBps = feeBps_;
    }

    function addLiquidity(uint256 amount0, uint256 amount1) external returns (uint256 shares) {
        if (amount0 == 0 || amount1 == 0) revert InvalidAmount();
        token0.transferFrom(msg.sender, address(this), amount0);
        token1.transferFrom(msg.sender, address(this), amount1);
        if (totalSupply() == 0) {
            shares = _sqrt(amount0 * amount1);
        } else {
            shares = _min((amount0 * totalSupply()) / reserve0, (amount1 * totalSupply()) / reserve1);
        }
        require(shares > 0, "shares zero");
        _mint(msg.sender, shares);
        _sync();
        emit LiquidityAdded(msg.sender, amount0, amount1, shares);
    }

    function removeLiquidity(uint256 shares) external returns (uint256 amount0, uint256 amount1) {
        if (shares == 0) revert InvalidAmount();
        uint256 currentSupply = totalSupply();
        amount0 = (shares * reserve0) / currentSupply;
        amount1 = (shares * reserve1) / currentSupply;
        require(amount0 > 0 && amount1 > 0, "amount zero");
        _burn(msg.sender, shares);
        token0.transfer(msg.sender, amount0);
        token1.transfer(msg.sender, amount1);
        _sync();
        emit LiquidityRemoved(msg.sender, shares, amount0, amount1);
    }

    function swap(address tokenIn, uint256 amountIn, uint256 minAmountOut) external returns (uint256 amountOut) {
        if (amountIn == 0) revert InvalidAmount();
        bool isToken0In = tokenIn == address(token0);
        if (!isToken0In && tokenIn != address(token1)) revert InvalidToken();
        IERC20 inToken = isToken0In ? token0 : token1;
        IERC20 outToken = isToken0In ? token1 : token0;
        uint256 reserveIn = isToken0In ? reserve0 : reserve1;
        uint256 reserveOut = isToken0In ? reserve1 : reserve0;
        inToken.transferFrom(msg.sender, address(this), amountIn);
        uint256 amountInWithFee = (amountIn * (10000 - feeBps)) / 10000;
        amountOut = (reserveOut * amountInWithFee) / (reserveIn + amountInWithFee);
        if (amountOut < minAmountOut || amountOut == 0) revert SlippageExceeded();
        outToken.transfer(msg.sender, amountOut);
        _sync();
        emit Swap(msg.sender, tokenIn, amountIn, amountOut);
    }

    function setFeeBps(uint256 newFeeBps) external onlyOwner {
        require(newFeeBps <= 100, "fee too high");
        feeBps = newFeeBps;
        emit FeeBpsUpdated(newFeeBps);
    }

    function _sync() internal {
        reserve0 = token0.balanceOf(address(this));
        reserve1 = token1.balanceOf(address(this));
    }

    function _min(uint256 a, uint256 b) private pure returns (uint256) {
        return a < b ? a : b;
    }

    function _sqrt(uint256 y) private pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = (y / 2) + 1;
            while (x < z) {
                z = x;
                x = ((y / x) + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }
}
