# Moving a mission's origin: protocol

Status: design. pymoos2 1.0.0 ships the pieces it builds on (`LocalFrame` with
an epoch, `to_spec`/`from_spec`, `distortion`, `reframe_*`); the participant
mixin and the coordinator app come next. The protocol is language neutral so
C++ apps can implement the same contract.

## Why

Most IvP helm behaviors work in local SI coordinates, meters east and north
of a fixed origin. Any flat frame distorts
away from its origin: at mid latitudes a UTM frame is off by about 0.03% in
scale and 1.4° in heading 100 km out, and by 0.8% and 7° at 1,000 km. A
glider, an aerial vehicle or a long transit leaves that region. Moving the
origin with the vehicle keeps x/y small and accurate. Lat/lon never change;
x/y change once, deliberately, everywhere at the same instant.

## Terms

- **Frame**: origin lat/lon, projection (`utm` or `aeqd`) and **epoch**, a
  counter that increases by one with every move. Written as a frame spec:
  `epoch=3,lat=42.358456,lon=-71.087589,proj=utm,zone=19N`.
- **Participant**: an app that holds x/y state (waypoints, polygons, estimator
  state, anything converted with the origin). Apps that only pass x/y through
  without storing it are not participants.
- **Coordinator**: the one app per community that proposes, commits and aborts
  moves.

## Variables

| Variable | Posted by | Value |
|---|---|---|
| `GEO_ORIGIN` | coordinator | the frame in force, as a frame spec. Posted at start, after every commit, and every 10 s |
| `GEO_ORIGIN_PARTICIPANT` | each participant | `app=<name>`, at start and after every reconnect |
| `GEO_ORIGIN_PROPOSE` | coordinator | `<frame spec of the next frame>,commit_utc=<MOOS time>,deadline_utc=<MOOS time>` |
| `GEO_ORIGIN_ACK` | each participant | `app=<name>,epoch=<n>,ready=true` or `...,ready=false,reason=<text>` |
| `GEO_ORIGIN_COMMIT` | coordinator | `epoch=<n>,commit_utc=<MOOS time>` |
| `GEO_ORIGIN_ABORT` | coordinator | `epoch=<n>,reason=<text>` |
| `GEO_ORIGIN_GATE` | mission (helm, operator) | `true` when a move is allowed now |
| `FRAME_DISTORTION` | coordinator or monitor | distortion at the vehicle, as `pymoos2.geodesy.Distortion.to_spec()` |

## States

```
STABLE(n) --propose--> PROPOSED(n+1) --all ready--> PREPARED(n+1) --commit_utc--> STABLE(n+1)
                          |                             |
                          +--- deadline, ready=false, ---+--> ABORTED --> STABLE(n)
                               gate closed, coordinator restart
```

1. **STABLE(n).** Everyone uses frame n.
2. **PROPOSED(n+1).** The coordinator posts `GEO_ORIGIN_PROPOSE` only while
   `GEO_ORIGIN_GATE` is true. `commit_utc` lies at least one participant
   AppTick period plus one comms round trip after `deadline_utc`.
3. **Each participant** converts every stored x/y item into frame n+1 exactly,
   through lat/lon (`reframe_*` in pymoos2), and keeps both versions. It then
   posts `ready=true`. A participant that cannot convert posts `ready=false`
   with a reason.
4. **PREPARED(n+1)** when every registered participant is ready before
   `deadline_utc`. The coordinator posts `GEO_ORIGIN_COMMIT`.
5. **At `commit_utc`** every participant switches to frame n+1 on its first
   iteration whose MOOS time is at or after `commit_utc`, and drops the frame n
   copies. The coordinator posts `GEO_ORIGIN` for n+1.
6. **Abort** on any `ready=false`, a missing ack at `deadline_utc`, the gate
   closing before `commit_utc`, or a coordinator restart. Participants discard
   their n+1 copies and stay on frame n.

## The timestamp rule

Many x/y variables are plain doubles (`NAV_X`, `NAV_Y`) and cannot carry an
epoch. Every MOOS message carries its posting time, so the frame of any x/y
message is decided by that time: before `commit_utc` it is frame n, at or
after it frame n+1. Producers switch exactly at `commit_utc`; consumers
convert any frame n message that arrives late. No message is ambiguous.

## Triggers

The coordinator proposes when a configured condition holds and has held for a
hold time, so it does not oscillate:

- distance from the origin above `max_range_m`;
- `|scale_ppm|`, `|convergence_deg|`, `|range_error_m|` or `|bearing_error_deg|`
  above their limits (pFrameMonitor's thresholds are a starting point);
- an operator request.

The new origin is the vehicle's position, or a planned point ahead of it so the
next leg sits near the origin.

## Failure handling

- A participant that registers after a commit reads `GEO_ORIGIN` and starts in
  the current frame.
- A participant that restarts during PROPOSED does not ack; the move aborts.
- A coordinator restart aborts any move in flight; it re-posts `GEO_ORIGIN` from
  the last committed frame, which it keeps on disk.
- `GEO_ORIGIN` repeating every 10 s lets any app detect a frame it missed: an
  epoch newer than its own means it must resynchronize from lat/lon.

## Apps that do not take part

Stock C++ apps read `LatOrigin` once at startup. In a mission that moves its
origin they must either implement this protocol, or have their x/y state
re-posted for them in the new frame by a participant acting on their behalf
(for example re-sending helm behavior updates with converted points), or be
restarted with the new origin after a commit.
