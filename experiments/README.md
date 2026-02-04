# Experiments Directory

This directory contains **simulation and test scaffolding** for the Mycorrhiza tracker.

## Purpose

The code here is for:
- Testing the core tracker with synthetic agents
- Exploring different agent behaviors
- Parameter sweeps and experiments
- Generating test scenarios

## NOT Part of Core

**Important:** This is NOT production code.

- The core tracker (`core/`) does NOT depend on this
- Production usage does NOT use these simulations
- These are tools FOR testing, not part of the system itself

## Philosophy

> "Simulation is for understanding the tracker, not part of the tracker."

The tracker tracks **reality** (real predictions, real outcomes).
The experiments **generate synthetic data** to test the tracker.

One-way dependency:
```
experiments/ → core/   (experiments USE core)
core/ ↛ experiments/   (core doesn't know about experiments)
```

## Files

- `synthetic_agents.py` - Agent personality simulation (optimist, pessimist, etc.)
  - Used for testing calibration updates
  - Not used in production
  - Clearly labeled as simulation

## Usage

Only use these when:
1. Testing the core tracker with synthetic data
2. Exploring "what if" scenarios
3. Demonstrating the system with generated examples

Never use in production where real Claude Code predictions are tracked.
