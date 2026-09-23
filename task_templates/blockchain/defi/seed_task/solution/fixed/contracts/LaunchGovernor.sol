// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";

contract LaunchGovernor {
    error ThresholdNotMet();
    error InvalidProposal();
    error InvalidLengths();
    error VotingNotOpen();
    error AlreadyVoted();
    error NoVotingWeight();
    error ProposalNotSuccessful();
    error ProposalNotQueued();
    error TimelockActive();
    error ProposalAlreadyExecuted();
    error ExecutionFailed();

    ERC20Votes public immutable governanceToken;
    uint256 public immutable proposalThreshold;
    uint256 public immutable quorumVotes;
    uint256 public immutable votingDelayBlocks;
    uint256 public immutable votingPeriodBlocks;
    uint256 public immutable timelockDelaySeconds;
    uint256 public proposalCount;

    struct Proposal {
        address proposer;
        uint256 snapshotBlock;
        uint256 deadlineBlock;
        uint256 eta;
        uint256 forVotes;
        uint256 againstVotes;
        bool queued;
        bool executed;
        address[] targets;
        uint256[] values;
        bytes[] calldatas;
    }

    mapping(uint256 => Proposal) private _proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event ProposalCreated(uint256 indexed proposalId, address indexed proposer);
    event VoteCast(address indexed voter, uint256 indexed proposalId, bool support, uint256 weight);
    event ProposalQueued(uint256 indexed proposalId, uint256 eta);
    event ProposalExecuted(uint256 indexed proposalId);

    constructor(
        address governanceToken_,
        uint256 proposalThreshold_,
        uint256 quorumVotes_,
        uint256 votingDelayBlocks_,
        uint256 votingPeriodBlocks_,
        uint256 timelockDelaySeconds_
    ) {
        governanceToken = ERC20Votes(governanceToken_);
        proposalThreshold = proposalThreshold_;
        quorumVotes = quorumVotes_;
        votingDelayBlocks = votingDelayBlocks_;
        votingPeriodBlocks = votingPeriodBlocks_;
        timelockDelaySeconds = timelockDelaySeconds_;
    }

    function propose(address[] memory targets, uint256[] memory values, bytes[] memory calldatas)
        external
        returns (uint256 proposalId)
    {
        if (governanceToken.getPastVotes(msg.sender, block.number - 1) < proposalThreshold) {
            revert ThresholdNotMet();
        }
        if (targets.length == 0 || targets.length != values.length || targets.length != calldatas.length) {
            revert InvalidLengths();
        }
        proposalId = ++proposalCount;
        Proposal storage proposal = _proposals[proposalId];
        proposal.proposer = msg.sender;
        proposal.snapshotBlock = block.number + votingDelayBlocks;
        proposal.deadlineBlock = proposal.snapshotBlock + votingPeriodBlocks;
        for (uint256 i = 0; i < targets.length; i++) {
            proposal.targets.push(targets[i]);
            proposal.values.push(values[i]);
            proposal.calldatas.push(calldatas[i]);
        }
        emit ProposalCreated(proposalId, msg.sender);
    }

    function castVote(uint256 proposalId, bool support) external {
        Proposal storage proposal = _proposals[proposalId];
        if (proposal.proposer == address(0)) revert InvalidProposal();
        if (block.number < proposal.snapshotBlock || block.number > proposal.deadlineBlock) revert VotingNotOpen();
        if (hasVoted[proposalId][msg.sender]) revert AlreadyVoted();
        uint256 weight = governanceToken.getPastVotes(msg.sender, proposal.snapshotBlock);
        if (weight == 0) revert NoVotingWeight();
        hasVoted[proposalId][msg.sender] = true;
        if (support) {
            proposal.forVotes += weight;
        } else {
            proposal.againstVotes += weight;
        }
        emit VoteCast(msg.sender, proposalId, support, weight);
    }

    function queue(uint256 proposalId) external {
        Proposal storage proposal = _proposals[proposalId];
        if (proposal.proposer == address(0)) revert InvalidProposal();
        if (proposal.queued) revert ProposalNotSuccessful();
        if (block.number <= proposal.deadlineBlock) revert VotingNotOpen();
        if (proposal.forVotes < quorumVotes || proposal.forVotes <= proposal.againstVotes) revert ProposalNotSuccessful();
        proposal.queued = true;
        proposal.eta = block.timestamp + timelockDelaySeconds;
        emit ProposalQueued(proposalId, proposal.eta);
    }

    function execute(uint256 proposalId) external {
        Proposal storage proposal = _proposals[proposalId];
        if (proposal.proposer == address(0)) revert InvalidProposal();
        if (!proposal.queued) revert ProposalNotQueued();
        if (proposal.executed) revert ProposalAlreadyExecuted();
        if (block.timestamp < proposal.eta) revert TimelockActive();
        proposal.executed = true;
        for (uint256 i = 0; i < proposal.targets.length; i++) {
            (bool ok, ) = proposal.targets[i].call{value: proposal.values[i]}(proposal.calldatas[i]);
            if (!ok) revert ExecutionFailed();
        }
        emit ProposalExecuted(proposalId);
    }

    function getProposal(uint256 proposalId)
        external
        view
        returns (
            address proposer,
            uint256 snapshotBlock,
            uint256 deadlineBlock,
            uint256 eta,
            uint256 forVotes,
            uint256 againstVotes,
            bool queued,
            bool executed
        )
    {
        Proposal storage proposal = _proposals[proposalId];
        if (proposal.proposer == address(0)) revert InvalidProposal();
        return (
            proposal.proposer,
            proposal.snapshotBlock,
            proposal.deadlineBlock,
            proposal.eta,
            proposal.forVotes,
            proposal.againstVotes,
            proposal.queued,
            proposal.executed
        );
    }
}
