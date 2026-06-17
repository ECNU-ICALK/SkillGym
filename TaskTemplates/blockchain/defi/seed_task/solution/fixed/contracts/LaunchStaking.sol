// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract LaunchStaking is Ownable {
    error InvalidAmount();
    error RewardPeriodActive();
    error RewardRateZero();
    error NotDistributor();
    error InsufficientStake();
    error UnderfundedRewardPool();

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

    modifier updateReward(address account) {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = lastTimeRewardApplicable();
        if (account != address(0)) {
            rewards[account] = earned(account);
            userRewardPerTokenPaid[account] = rewardPerTokenStored;
        }
        _;
    }

    function lastTimeRewardApplicable() public view returns (uint256) {
        return block.timestamp < periodFinish ? block.timestamp : periodFinish;
    }

    function rewardPerToken() public view returns (uint256) {
        if (totalStaked == 0) return rewardPerTokenStored;
        return rewardPerTokenStored + (((lastTimeRewardApplicable() - lastUpdateTime) * rewardRate * 1e18) / totalStaked);
    }

    function earned(address account) public view returns (uint256) {
        return ((balances[account] * (rewardPerToken() - userRewardPerTokenPaid[account])) / 1e18) + rewards[account];
    }

    function fundProgram(uint256 rewardAmount) external onlyDistributor updateReward(address(0)) {
        if (rewardAmount == 0) revert InvalidAmount();
        rewardsToken.transferFrom(msg.sender, address(this), rewardAmount);
        totalFunded += rewardAmount;
        if (block.timestamp >= periodFinish) {
            rewardRate = rewardAmount / rewardsDuration;
        } else {
            uint256 remaining = periodFinish - block.timestamp;
            uint256 leftover = remaining * rewardRate;
            rewardRate = (rewardAmount + leftover) / rewardsDuration;
        }
        if (rewardRate == 0) revert RewardRateZero();
        if (rewardRate * rewardsDuration > rewardsToken.balanceOf(address(this))) revert UnderfundedRewardPool();
        lastUpdateTime = block.timestamp;
        periodFinish = block.timestamp + rewardsDuration;
        emit Funded(rewardAmount);
    }

    function stake(uint256 amount) external updateReward(msg.sender) {
        if (amount == 0) revert InvalidAmount();
        totalStaked += amount;
        balances[msg.sender] += amount;
        stakingToken.transferFrom(msg.sender, address(this), amount);
        emit Staked(msg.sender, amount);
    }

    function withdraw(uint256 amount) public updateReward(msg.sender) {
        if (amount == 0) revert InvalidAmount();
        if (amount > balances[msg.sender]) revert InsufficientStake();
        totalStaked -= amount;
        balances[msg.sender] -= amount;
        stakingToken.transfer(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    function getReward() public updateReward(msg.sender) returns (uint256 reward) {
        reward = rewards[msg.sender];
        if (reward > 0) {
            rewards[msg.sender] = 0;
            totalClaimed += reward;
            rewardsToken.transfer(msg.sender, reward);
            emit RewardPaid(msg.sender, reward);
        }
    }

    function exit() external returns (uint256 reward) {
        withdraw(balances[msg.sender]);
        reward = getReward();
    }

    function setRewardsDuration(uint256 newDuration) external onlyOwner {
        if (newDuration == 0) revert InvalidAmount();
        if (block.timestamp <= periodFinish) revert RewardPeriodActive();
        rewardsDuration = newDuration;
        emit RewardsDurationUpdated(newDuration);
    }
}
