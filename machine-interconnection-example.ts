/**
 * Machine Interconnection Example
 *
 * Demonstrates how machines can be interconnected through a shared
 * 256-dimensional perceptual space (En).
 *
 * Architecture:
 * - En: 256-dimensional perceptual space representing our view of reality
 * - Multi-Step Machine views En[0:3] and writes to En[3:5]
 * - RS Flip-Flop views En[3:5] (output of Multi-Step) and writes to En[6:8]
 *
 * This creates a data flow: Input -> Multi-Step -> RS Flip-Flop -> Output
 */

import { Machine } from '../src/models/Machine.js';
import { CriticalEventSequence } from '../src/models/CriticalEventSequence.js';
import { RealityVector } from '../src/models/RealityVector.js';
import { PerceptualSpace } from '../src/models/PerceptualSpace.js';
import { VectorState, ComparatorType, ArbiterRule } from '../src/models/types.js';
import type { PerceptualMapping } from '../src/models/types.js';

/**
 * Create a Multi-Step State Machine
 *
 * Perceptual Mapping:
 * - Input: offset=0, length=3 (reads En[0:3])
 * - Output: offset=3, length=2 (writes to En[3:5])
 */
function createMultiStepMachine(): Machine {
  const machine = new Machine(
    'Multi-Step State Machine',
    'A multi-step state machine with conditional outputs',
    { category: 'state-machine' },
    ArbiterRule.PASSTHROUGH
  );

  // Sequence 1: State A -> State B -> Output X
  const seq1 = new CriticalEventSequence(
    'Multi-Step Sequence 1',
    'Three-step sequence producing output X'
  );

  // State A: Initial trigger (input [1, 0, 0])
  const stateA = new RealityVector(
    'State A',
    [
      { value: 1, comparatorType: ComparatorType.EQUALS },
      { value: 0, comparatorType: ComparatorType.EQUALS },
      { value: 0, comparatorType: ComparatorType.EQUALS }
    ],
    VectorState.ACTIVE,
    { description: 'Initial state' }
  );

  // State B: Intermediate (input [0, 1, 0])
  const stateB = new RealityVector(
    'State B',
    [
      { value: 0, comparatorType: ComparatorType.EQUALS },
      { value: 1, comparatorType: ComparatorType.EQUALS },
      { value: 0, comparatorType: ComparatorType.EQUALS }
    ],
    VectorState.INACTIVE,
    { description: 'Intermediate state' }
  );

  // Output X: Final state with output (input [0, 0, 1])
  const outputX = new RealityVector(
    'Output X',
    [
      { value: 0, comparatorType: ComparatorType.EQUALS },
      { value: 0, comparatorType: ComparatorType.EQUALS },
      { value: 1, comparatorType: ComparatorType.EQUALS }
    ],
    VectorState.INACTIVE,
    {
      description: 'Final state producing output',
      producesOutput: true,
      outputVector: [1, 0] // Output to En[3:5]
    }
  );

  seq1.addVector(stateA);
  seq1.addVector(stateB);
  seq1.addVector(outputX);
  machine.addSequence(seq1);

  // Sequence 2: State C -> State D -> Output Y
  const seq2 = new CriticalEventSequence(
    'Multi-Step Sequence 2',
    'Alternative path producing output Y'
  );

  // State C: Alternative initial (input [1, 1, 0])
  const stateC = new RealityVector(
    'State C',
    [
      { value: 1, comparatorType: ComparatorType.EQUALS },
      { value: 1, comparatorType: ComparatorType.EQUALS },
      { value: 0, comparatorType: ComparatorType.EQUALS }
    ],
    VectorState.ACTIVE,
    { description: 'Alternative initial state' }
  );

  // Output Y: Direct output (input [0, 1, 1])
  const outputY = new RealityVector(
    'Output Y',
    [
      { value: 0, comparatorType: ComparatorType.EQUALS },
      { value: 1, comparatorType: ComparatorType.EQUALS },
      { value: 1, comparatorType: ComparatorType.EQUALS }
    ],
    VectorState.INACTIVE,
    {
      description: 'Alternative output',
      producesOutput: true,
      outputVector: [0, 1] // Output to En[3:5]
    }
  );

  seq2.addVector(stateC);
  seq2.addVector(outputY);
  machine.addSequence(seq2);

  // Set perceptual mapping
  const mapping: PerceptualMapping = {
    input: { offset: 0, length: 3 },
    output: { offset: 3, length: 2 }
  };
  machine.setPerceptualMapping(mapping);

  return machine;
}

/**
 * Create an RS Flip-Flop Machine
 *
 * Perceptual Mapping:
 * - Input: offset=3, length=2 (reads En[3:5] - output of Multi-Step)
 * - Output: offset=6, length=2 (writes to En[6:8])
 */
function createRSFlipFlopMachine(): Machine {
  const machine = new Machine(
    'RS Flip-Flop',
    'Set-Reset flip-flop with memory',
    { category: 'memory' },
    ArbiterRule.PASSTHROUGH
  );

  // Sequence 1: Set operation (S=1, R=0 -> Q=1)
  const setSeq = new CriticalEventSequence(
    'RS Set Sequence',
    'Set the flip-flop output to 1'
  );

  const setInput = new RealityVector(
    'Set Input',
    [
      { value: 1, comparatorType: ComparatorType.EQUALS }, // S=1
      { value: 0, comparatorType: ComparatorType.EQUALS }  // R=0
    ],
    VectorState.ACTIVE,
    {
      description: 'Set command',
      producesOutput: true,
      outputVector: [1, 0] // Q=1, Q̄=0
    }
  );

  setSeq.addVector(setInput);
  machine.addSequence(setSeq);

  // Sequence 2: Reset operation (S=0, R=1 -> Q=0)
  const resetSeq = new CriticalEventSequence(
    'RS Reset Sequence',
    'Reset the flip-flop output to 0'
  );

  const resetInput = new RealityVector(
    'Reset Input',
    [
      { value: 0, comparatorType: ComparatorType.EQUALS }, // S=0
      { value: 1, comparatorType: ComparatorType.EQUALS }  // R=1
    ],
    VectorState.ACTIVE,
    {
      description: 'Reset command',
      producesOutput: true,
      outputVector: [0, 1] // Q=0, Q̄=1
    }
  );

  resetSeq.addVector(resetInput);
  machine.addSequence(resetSeq);

  // Sequence 3: Hold state (S=0, R=0 -> maintain)
  const holdSeq = new CriticalEventSequence(
    'RS Hold Sequence',
    'Maintain current state'
  );

  const holdInput = new RealityVector(
    'Hold Input',
    [
      { value: 0, comparatorType: ComparatorType.EQUALS }, // S=0
      { value: 0, comparatorType: ComparatorType.EQUALS }  // R=0
    ],
    VectorState.ACTIVE,
    {
      description: 'Hold command - no output change'
    }
  );

  holdSeq.addVector(holdInput);
  machine.addSequence(holdSeq);

  // Set perceptual mapping
  const mapping: PerceptualMapping = {
    input: { offset: 3, length: 2 },
    output: { offset: 6, length: 2 }
  };
  machine.setPerceptualMapping(mapping);

  return machine;
}

/**
 * Run the interconnection example
 */
export function runInterconnectionExample() {
  console.log('=== Machine Interconnection Example ===\n');

  // Create the shared 256-dimensional perceptual space
  const perceptualSpace = new PerceptualSpace(256);
  console.log('✓ Created 256-dimensional perceptual space (En)');

  // Create the machines
  const multiStepMachine = createMultiStepMachine();
  const rsFlipFlop = createRSFlipFlopMachine();
  console.log(`✓ Created Multi-Step Machine (input: En[0:3], output: En[3:5])`);
  console.log(`✓ Created RS Flip-Flop (input: En[3:5], output: En[6:8])\n`);

  // Display machine configurations
  console.log('Machine Configurations:');
  console.log('----------------------');
  console.log(`Multi-Step Machine:`);
  console.log(`  Input mapping:  offset=${multiStepMachine.perceptualMapping?.input.offset}, length=${multiStepMachine.perceptualMapping?.input.length}`);
  console.log(`  Output mapping: offset=${multiStepMachine.perceptualMapping?.output.offset}, length=${multiStepMachine.perceptualMapping?.output.length}`);
  console.log(`\nRS Flip-Flop:`);
  console.log(`  Input mapping:  offset=${rsFlipFlop.perceptualMapping?.input.offset}, length=${rsFlipFlop.perceptualMapping?.input.length}`);
  console.log(`  Output mapping: offset=${rsFlipFlop.perceptualMapping?.output.offset}, length=${rsFlipFlop.perceptualMapping?.output.length}\n`);

  // Example 1: Trigger Multi-Step sequence 1
  console.log('=== Example 1: Multi-Step Sequence 1 ===');
  console.log('Setting En[0:3] = [1, 0, 0] (State A)');
  perceptualSpace.updateRegion(0, [1, 0, 0]);

  console.log('\nProcessing through Multi-Step Machine...');
  let result1 = multiStepMachine.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  Matched vectors: ${Array.from(result1.sequenceResults.values())
    .flatMap(r => r.matchedVectors).join(', ')}`);
  console.log(`  Machine output: ${result1.machineOutput?.vector || 'none'}`);
  console.log(`  En[3:5] = ${JSON.stringify(perceptualSpace.getRegion(3, 2))}`);

  // Continue sequence: State A -> State B
  console.log('\nSetting En[0:3] = [0, 1, 0] (State B)');
  perceptualSpace.updateRegion(0, [0, 1, 0]);
  result1 = multiStepMachine.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  Machine output: ${result1.machineOutput?.vector || 'none'}`);
  console.log(`  En[3:5] = ${JSON.stringify(perceptualSpace.getRegion(3, 2))}`);

  // Final state: State B -> Output X
  console.log('\nSetting En[0:3] = [0, 0, 1] (Output X)');
  perceptualSpace.updateRegion(0, [0, 0, 1]);
  result1 = multiStepMachine.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  Machine output: ${JSON.stringify(result1.machineOutput?.vector)}`);
  console.log(`  En[3:5] = ${JSON.stringify(perceptualSpace.getRegion(3, 2))} ← Output from Multi-Step`);

  // Process through RS Flip-Flop
  console.log('\nProcessing through RS Flip-Flop (reads En[3:5])...');
  const result2 = rsFlipFlop.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  RS Flip-Flop input: ${JSON.stringify(perceptualSpace.getRegion(3, 2))}`);
  console.log(`  RS Flip-Flop output: ${JSON.stringify(result2.machineOutput?.vector)}`);
  console.log(`  En[6:8] = ${JSON.stringify(perceptualSpace.getRegion(6, 2))} ← Output from RS Flip-Flop\n`);

  // Example 2: Trigger Multi-Step sequence 2
  console.log('=== Example 2: Multi-Step Sequence 2 ===');
  perceptualSpace.reset();
  console.log('Reset perceptual space');

  console.log('Setting En[0:3] = [1, 1, 0] (State C)');
  perceptualSpace.updateRegion(0, [1, 1, 0]);
  result1 = multiStepMachine.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  Machine output: ${result1.machineOutput?.vector || 'none'}`);

  console.log('\nSetting En[0:3] = [0, 1, 1] (Output Y)');
  perceptualSpace.updateRegion(0, [0, 1, 1]);
  result1 = multiStepMachine.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  Machine output: ${JSON.stringify(result1.machineOutput?.vector)}`);
  console.log(`  En[3:5] = ${JSON.stringify(perceptualSpace.getRegion(3, 2))} ← Output from Multi-Step`);

  // Process through RS Flip-Flop (should reset)
  console.log('\nProcessing through RS Flip-Flop (reads En[3:5])...');
  const result3 = rsFlipFlop.processInputFromPerceptualSpace(perceptualSpace);
  console.log(`  RS Flip-Flop input: ${JSON.stringify(perceptualSpace.getRegion(3, 2))}`);
  console.log(`  RS Flip-Flop output: ${JSON.stringify(result3.machineOutput?.vector)}`);
  console.log(`  En[6:8] = ${JSON.stringify(perceptualSpace.getRegion(6, 2))} ← Output from RS Flip-Flop\n`);

  // Display final perceptual space state
  console.log('=== Final Perceptual Space State ===');
  console.log(`En[0:3]  (Multi-Step input):  ${JSON.stringify(perceptualSpace.getRegion(0, 3))}`);
  console.log(`En[3:5]  (Multi-Step output): ${JSON.stringify(perceptualSpace.getRegion(3, 2))}`);
  console.log(`En[6:8]  (RS Flip-Flop output): ${JSON.stringify(perceptualSpace.getRegion(6, 2))}`);
  console.log(`En[8:16] (unused): ${JSON.stringify(perceptualSpace.getRegion(8, 8))}`);
}

// Run the example if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runInterconnectionExample();
}
