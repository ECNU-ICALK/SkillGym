// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract GovernanceToken is ERC20, ERC20Permit, ERC20Votes, Ownable {
    uint256 public immutable cap;
    uint8 private immutable _customDecimals;

    constructor(
        string memory name_,
        string memory symbol_,
        uint8 decimals_,
        uint256 cap_,
        address[] memory recipients,
        uint256[] memory amounts
    ) ERC20(name_, symbol_) ERC20Permit(name_) {
        require(recipients.length == amounts.length, "length mismatch");
        cap = cap_;
        _customDecimals = decimals_;
        uint256 runningTotal = 0;
        for (uint256 i = 0; i < recipients.length; i++) {
            runningTotal += amounts[i];
            require(runningTotal <= cap_, "cap exceeded");
            _mint(recipients[i], amounts[i]);
        }
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= cap, "cap exceeded");
        _mint(to, amount);
    }

    function decimals() public view override returns (uint8) {
        return _customDecimals;
    }

    function _afterTokenTransfer(address from, address to, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }

    function _mint(address to, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }

    function _burn(address account, uint256 amount) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }
}
