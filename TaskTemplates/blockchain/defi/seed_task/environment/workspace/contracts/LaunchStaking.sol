// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract LaunchStaking is Ownable {
    error InvalidAmount();
    error NotImplemented();
    error NotDistributor();

    IERC20 public immutable stakingToken;
    IERC20 public immutable rewardsToken;
    address public rewardsDistributor;

    uint256 public periodFinish;
    uint256 public rewardsDuration;
    uint256 public rewardRate;
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;
    uint256 public totalStaked;
    uint256 public totalFunded;
    uint256 public totalClaimed;

    mapping(address => uint256) public balances;
    mapping(address => uint256) public userRewardPerTokenPaid;
    mapping(address => uint256) public rewards;

    event Funded(uint256 rewardAmount);
    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardPaid(address indexed user, uint256 reward);
    event RewardsDurationUpdated(uint256 newDuration);

    constructor(address stakingToken_, address rewardsToken_, address distributor_, uint256 rewardsDuration_) {
        stakingToken = IERC20(stakingToken_);
        rewardsToken = IERC20(rewardsToken_);
        rewardsDistributor = distributor_;
        rewardsDuration = rewardsDuration_;
    }

    modifier onlyDistributor() {
        if (msg.sender != rewardsDistributor) revert NotDistributor();
        _;
    }

    function lastTimeRewardApplicable() public view returns (uint256) {
        return block.timestamp < periodFinish ? block.timestamp : periodFinish;
    }

    function rewardPerToken() public view returns (uint256) {
        if (totalStaked == 0) return rewardPerTokenStored;
        return rewardPerTokenStored;
    }

    function earned(address account) public view returns (uint256) {
        account;
        revert NotImplemented();
    }

    function fundProgram(uint256 rewardAmount) external onlyDistributor {
        if (rewardAmount == 0) revert InvalidAmount();
        rewardsToken.transferFrom(msg.sender, address(this), rewardAmount);
        totalFunded += rewardAmount;
        revert NotImplemented();
    }

    function stake(uint256 amount) external {
        if (amount == 0) revert InvalidAmount();
        revert NotImplemented();
    }

    function withdraw(uint256 amount) public {
        if (amount == 0) revert InvalidAmount();
        revert NotImplemented();
    }

    function getReward() public returns (uint256 reward) {
        reward;
        revert NotImplemented();
    }

    function exit() external returns (uint256 reward) {
        reward;
        revert NotImplemented();
    }

    function setRewardsDuration(uint256 newDuration) external onlyOwner {
        if (newDuration == 0) revert InvalidAmount();
        rewardsDuration = newDuration;
        emit RewardsDurationUpdated(newDuration);
    }
}
