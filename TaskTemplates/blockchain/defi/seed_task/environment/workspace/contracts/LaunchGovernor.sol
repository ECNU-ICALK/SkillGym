// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";

contract LaunchGovernor {
    error ThresholdNotMet();
    error InvalidProposal();
    error NotImplemented();

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
        targets;
        values;
        calldatas;
        proposalId = ++proposalCount;
        emit ProposalCreated(proposalId, msg.sender);
        revert NotImplemented();
    }

    function castVote(uint256 proposalId, bool support) external {
        proposalId;
        support;
        revert NotImplemented();
    }

    function queue(uint256 proposalId) external {
        proposalId;
        revert NotImplemented();
    }

    function execute(uint256 proposalId) external {
        proposalId;
        revert NotImplemented();
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
