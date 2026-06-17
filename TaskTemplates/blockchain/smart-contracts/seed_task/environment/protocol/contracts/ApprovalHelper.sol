// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

library ApprovalHelper {
    using SafeERC20 for IERC20;

    function resetAndApprove(IERC20 token, address spender, uint256 amount) internal {
        token.safeApprove(spender, 0);
        token.safeApprove(spender, amount);
    }
}
