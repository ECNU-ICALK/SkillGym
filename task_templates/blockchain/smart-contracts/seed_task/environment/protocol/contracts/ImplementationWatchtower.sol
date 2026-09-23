// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ImplementationWatchtower {
    mapping(address => bytes32) public lastObservedCodehash;

    event TokenImplementationObserved(address indexed token, bytes32 codehash);

    function recordImplementation(address token) external {
        bytes32 observed = extcodehash(token);
        lastObservedCodehash[token] = observed;
        emit TokenImplementationObserved(token, observed);
    }
}
