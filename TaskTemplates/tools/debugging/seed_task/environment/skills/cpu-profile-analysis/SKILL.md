---
name: cpu-profile-analysis
description: "Analyze V8/Chrome CPU profiles (.cpuprofile) and DevTools trace files (Trace-*.json). Use when: profiling performance, investigating slow functions, comparing code paths, finding bottlenecks, analyzing timeToRequest, understanding call trees from sampling profiler data, analyzing layout/paint/rendering, investigating user timing marks."
---

# Analyze Performance Profiles

Analyze `.cpuprofile` files (V8 sampling profiler) and DevTools trace files (`Trace-*.json`, Chrome Trace Event Format) to find performance bottlenecks, compare code paths, and understand timing.

## When to Use
- User provides a `.cpuprofile` or `Trace-*.json` file and wants to understand performance
- Investigating why one code path is slower than another
- Finding what functions consume the most time
- Comparing "before/after" or "old/new" implementations in a single profile
- Investigating layout thrashing, long tasks, or rendering bottlenecks (trace files)
- Analyzing VS Code user timing marks like `code/didResolveTextFileEditorModel` (trace files)
- Understanding multi-process behavior (Browser, Renderer, GPU processes in trace files)

## Detecting File Type

- **`.cpuprofile`**: Top-level JSON with `nodes`, `samples`, `timeDeltas` keys. Created by the VS Code profiler.
- **`Trace-*.json`**: Top-level JSON with `traceEvents` array (and optional `metadata`). Created by Chrome/Electron DevTools (Performance tab). These are richer than `.cpuprofile` -- they contain CPU samples, layout/paint events, user timing marks, GC events, input events, and multi-process data.

## Key Concepts

- **Sampling profiler**: The profiler periodically snapshots the call stack. Not every function appears -- only those on the stack when the profiler sampled. Don't expect exact function names; look for patterns and nearby activity.
- **Self time**: Time spent in the function itself (the leaf/innermost frame).
- **Total time**: Time the function was anywhere on the stack (includes callees).
- **Idle samples**: Frames labeled `(idle)`, `(program)`, or `(garbage collector)` represent no user code running.

---

## Part 1: `.cpuprofile` Files

### Profile Format

A `.cpuprofile` is JSON with these top-level keys:
- `nodes`: Array of call frame nodes forming a tree (each has `id`, `callFrame`, `children`)
- `samples`: Array of node IDs -- one per profiler tick, referencing the leaf (innermost) frame
- `timeDeltas`: Array of microsecond deltas between consecutive samples
- `startTime` / `endTime`: Absolute timestamps in microseconds
- `$vscode`: Optional VS Code metadata

### Procedure

### 1. Check File Size and Parse

Profile and trace files can exceed V8's string limit (~512MB). Always check the file size first and choose the right parsing strategy:

```javascript
import { readFileSync, statSync } from 'fs';

const stat = statSync(profilePath);
const sizeMB = stat.size / (1024 * 1024);
console.log(`File size: ${sizeMB.toFixed(0)}MB`);

let data;
if (sizeMB < 400) {
    // Small enough for JSON.parse
    data = JSON.parse(readFileSync(profilePath, 'utf8'));
} else {
    // Too large -- use Buffer-based extraction (see "Handling Huge Files" section)
    data = parseProfileFromBuffer(readFileSync(profilePath));
}
```

For files under ~400MB, `JSON.parse(readFileSync(..., 'utf8'))` works fine. For larger files, see the **Handling Huge Files** section below.

### 2. Reformat the File (small files only)

Profiles are often single-line JSON. Reformat for inspection (only if small enough):

```javascript
if (sizeMB < 400) {
    const data = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
    fs.writeFileSync(profilePath, JSON.stringify(data, null, 2));
}
```

### 3. Build Data Structures

Write a Node.js analysis script. Build these structures:

```javascript
// Node lookup
const nodeMap = new Map();       // id -> node
const parentMap = new Map();     // id -> parent id

// Absolute timestamps from deltas
const timestamps = [data.startTime];
for (let i = 0; i < data.timeDeltas.length; i++) {
    timestamps.push(timestamps[i] + data.timeDeltas[i]);
}

// Stack walker (leaf to root)
function getStack(sampleNodeId) {
    const stack = [];
    let id = sampleNodeId;
    while (id !== undefined) {
        const node = nodeMap.get(id);
        if (node) stack.push(node.callFrame.functionName);
        id = parentMap.get(id);
    }
    return stack; // [leaf, ..., root]
}
```

### 4. Identify Activity Regions

Split the timeline into buckets (e.g. 500ms) and find which contain relevant function names. Use marker functions related to the user's question to detect activity windows. Allow small gaps (1-2 empty buckets) when merging regions.

**Important**: Because this is a sampling profiler, don't require exact function names. Use sets of related marker functions and look for the broader flow.

### 5. Measure Timing Between Milestones

For questions like "time from X to Y":
1. Find the first non-idle sample containing a marker for X on the stack
2. Find the first sample containing a marker for Y on the stack
3. The gap in absolute timestamps is the approximate duration
4. List all non-idle samples between these points to see what work happens in the gap

### 6. Compare Code Paths

When comparing two implementations:
1. Identify the activity region for each
2. For each region, compute self-time per function (time attributed to the leaf frame)
3. Sort by self-time descending to find the top cost centers
4. Show the first N non-idle stacks in each region to visualize the startup sequence

### 7. Report Findings

Present results as:
- **Timeline**: When each activity region occurred relative to profile start
- **Duration**: How long each region lasted
- **Top functions by self-time**: Where CPU time was actually spent
- **Comparison table**: Side-by-side metrics when comparing paths
- **Stack traces**: Key sample stacks showing the critical path

---

## Part 2: DevTools Trace Files (`Trace-*.json`)

DevTools traces are the future of perf tracing for VS Code. They are created from the built-in Electron/Chrome DevTools Performance tab and contain far more information than `.cpuprofile` files.

### Trace Format

A `Trace-*.json` file has these top-level keys:
- `traceEvents`: Array of trace event objects (hundreds of thousands of entries)
- `metadata`: Object with `source`, `startTime`, `dataOrigin`, and optional DevTools state (breadcrumbs, annotations)

### Trace Event Structure

Each event in `traceEvents` follows the Chrome Trace Event Format:

```javascript
{
  "pid": 3406,
  "tid": 7534980,
  "ts": 200420830729,
  "ph": "X",
  "cat": "devtools.timeline",
  "name": "EventDispatch",
  "dur": 9,
  "tdur": 8,
  "args": { ... },
  "tts": 7078808
}
```

### Phase Types (`ph`)

| Phase | Name | Meaning |
|-------|------|---------|
| `X` | Complete | Event with duration (`dur` field). Most common. |
| `B` | Begin | Start of a duration event (paired with `E`). |
| `E` | End | End of a duration event (paired with `B`). |
| `I` | Instant | Point-in-time event (no duration). |
| `P` | Sample | CPU profiler sample. |
| `R` | Mark | Navigation timing mark. |
| `M` | Metadata | Process/thread name metadata. |
| `N` | Object Created | Object lifecycle tracking. |
| `D` | Object Destroyed | Object lifecycle tracking. |
| `s` | Flow Start | Async flow connection start. |
| `f` | Flow End | Async flow connection end. |
| `b` | Async Begin | Async event begin. |
| `e` | Async End | Async event end. |
| `n` | Async Instant | Async event instant. |

### Key Categories and What They Contain

| Category | What it captures |
|----------|-----------------|
| `disabled-by-default-devtools.timeline` | `RunTask`, `EvaluateScript`, `TracingStartedInBrowser` -- core task scheduling |
| `devtools.timeline` | `FunctionCall`, `EventDispatch`, `TimerInstall/Fire`, `PrePaint`, `Paint` -- main thread activity |
| `blink.user_timing` | VS Code performance marks (e.g. `code/willResolveTextFileEditorModel`, `code/didResolveTextFileEditorModel`) |
| `blink,devtools.timeline` | `UpdateLayoutTree`, `HitTest`, `IntersectionObserver`, `ParseAuthorStyleSheet` -- layout/rendering |
| `disabled-by-default-v8.cpu_profiler` | `Profile`, `ProfileChunk` -- embedded CPU profile data (same as `.cpuprofile` but chunked) |
| `v8` | `v8.callFunction`, `v8.newInstance`, `V8.DeoptimizeCode` -- V8 engine events |
| `v8,devtools.timeline` | `v8.compile` -- script compilation |
| `devtools.timeline,v8` | `MinorGC`, `MajorGC` -- garbage collection |
| `cppgc` | C++ GC events (Blink garbage collection) |
| `loading` | `LayoutShift`, `URLLoader` -- resource loading and layout shifts |
| `cc,benchmark,disabled-by-default-devtools.timeline.frame` | Frame pipeline events (`PipelineReporter`, `Commit`, etc.) |
| `__metadata` | `process_name`, `thread_name` -- process/thread identification |

### Processes and Threads

Trace files contain events from multiple processes:

| Process | Role | Key Thread |
|---------|------|------------|
| **Renderer** (pid varies) | VS Code's renderer process -- where JS runs | `CrRendererMain` (main thread) |
| **Browser** (pid varies) | Electron's main/browser process | `CrBrowserMain` |
| **GPU Process** (pid varies) | GPU compositing and rendering | `CrGpuMain`, `VizCompositorThread` |

Identify processes/threads via metadata events:
```javascript
const procNames = events.filter(e => e.name === 'process_name');
const threadNames = events.filter(e => e.name === 'thread_name');
```

For VS Code perf analysis, focus on the **Renderer process, CrRendererMain thread** -- this is where JavaScript execution, layout, and painting happen.

### Procedure

#### 1. Check File Size and Parse

Trace files are typically 50-200MB but can exceed V8's string limit (~512MB). Always check first:

```javascript
import { readFileSync, statSync } from 'fs';

const stat = statSync(tracePath);
const sizeMB = stat.size / (1024 * 1024);
console.log(`File size: ${sizeMB.toFixed(0)}MB`);

let data;
if (sizeMB < 400) {
    data = JSON.parse(readFileSync(tracePath, 'utf8'));
} else {
    data = parseTraceFromBuffer(readFileSync(tracePath));
}
const events = data.traceEvents;
```

#### 2. Reformat the File (small files only)

For small trace files, reformat for inspection:
```javascript
if (sizeMB < 400) {
    fs.writeFileSync(tracePath, JSON.stringify(data, null, 2));
}
```

#### 3. Build Data Structures

```javascript
const data = JSON.parse(fs.readFileSync(tracePath, 'utf8'));
const events = data.traceEvents;

const rendererPid = events.find(e => e.name === 'process_name' && e.args?.name === 'Renderer')?.pid;
const mainTid = events.find(e => e.name === 'thread_name' && e.pid === rendererPid && e.args?.name === 'CrRendererMain')?.tid;
const mainEvents = events.filter(e => e.pid === rendererPid && e.tid === mainTid);
```

#### 4. Analyze User Timing Marks

VS Code emits `performance.mark()` calls that appear as `blink.user_timing` events. These are the most direct way to measure VS Code-specific milestones:

```javascript
const userTimings = events.filter(e => e.cat?.includes('blink.user_timing') && !e.cat.includes('rail'));
```

#### 5. Analyze Long Tasks

Find expensive tasks on the main thread:
```javascript
const longTasks = mainEvents
    .filter(e => e.name === 'RunTask' && e.ph === 'X' && e.dur > 50000)
    .sort((a, b) => b.dur - a.dur);
```

#### 6. Analyze Function Calls

`FunctionCall` events include source location info:
```javascript
const funcCalls = mainEvents
    .filter(e => e.name === 'FunctionCall' && e.dur > 10000)
    .sort((a, b) => b.dur - a.dur);
```

#### 7. Analyze Layout and Rendering

Find layout thrashing and expensive paints:
```javascript
const layoutEvents = mainEvents.filter(e =>
    e.name === 'UpdateLayoutTree' || e.name === 'Layout' ||
    e.name === 'PrePaint' || e.name === 'Paint'
);
```

#### 8. Extract Embedded CPU Profile

Trace files contain the full CPU profile as `ProfileChunk` events. Reconstruct it:
```javascript
const profileEvent = events.find(e => e.name === 'Profile' && e.pid === rendererPid);
const chunks = events.filter(e => e.name === 'ProfileChunk' && e.pid === rendererPid && e.id === profileEvent.id);
```

#### 9. Analyze GC Pressure

```javascript
const gcEvents = mainEvents.filter(e => e.name === 'MinorGC' || e.name === 'MajorGC');
const totalGcTime = gcEvents.reduce((sum, e) => sum + (e.dur || 0), 0);
```

#### 10. Analyze Input Latency

```javascript
const dispatches = mainEvents.filter(e => e.name === 'EventDispatch');
const longHandlers = dispatches.filter(e => e.dur > 50000).sort((a, b) => b.dur - a.dur);
```

#### 11. Report Findings

Present results as:
- **Timeline**: When each activity region occurred relative to trace start
- **User timing marks**: VS Code milestone events and their timestamps
- **Long tasks**: Tasks > 50ms that block the main thread
- **Top functions by duration**: Where CPU time was spent, with source locations
- **Layout/rendering**: Expensive style recalculations and paints
- **GC pressure**: Total GC time and frequency
- **Input latency**: Slow event handlers that degrade responsiveness
- **Process breakdown**: What work happened in Browser vs Renderer vs GPU

## Tips

- Timestamps in both formats are microseconds. Divide by 1000 for milliseconds.
- Filter out idle/program/GC samples when measuring active CPU work.
- When the user asks about a gap, check if it's truly idle versus active work in unrelated code.
- Clean up any analysis scripts you create when done.
