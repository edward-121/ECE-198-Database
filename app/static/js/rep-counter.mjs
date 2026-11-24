// Angle (in degrees) at joint B formed by points A-B-C, e.g. hip-knee-ankle.
export function calculateAngle(pointA, pointB, pointC) {
  const vectorBA = {
    x: pointA.x - pointB.x,
    y: pointA.y - pointB.y,
    z: (pointA.z || 0) - (pointB.z || 0),
  };
  const vectorBC = {
    x: pointC.x - pointB.x,
    y: pointC.y - pointB.y,
    z: (pointC.z || 0) - (pointB.z || 0),
  };
  const magnitudeBA = Math.hypot(vectorBA.x, vectorBA.y, vectorBA.z);
  const magnitudeBC = Math.hypot(vectorBC.x, vectorBC.y, vectorBC.z);
  if (magnitudeBA === 0 || magnitudeBC === 0) return 0;

  const dotProduct = vectorBA.x * vectorBC.x
    + vectorBA.y * vectorBC.y
    + vectorBA.z * vectorBC.z;
  // Clamp to [-1, 1] so floating-point error can't make acos return NaN
  const cosine = Math.max(-1, Math.min(1, dotProduct / (magnitudeBA * magnitudeBC)));
  return Math.acos(cosine) * (180 / Math.PI);
}

// Maps an exercise name to a counter type, or null if it can't be auto-counted.
export function supportedExerciseType(name) {
  if (/\bsquats?\b/i.test(name)) return "squat";
  if (/\bbicep curls?\b/i.test(name)) return "curl";
  return null;
}

// Returns the given landmarks (plus their average visibility) only if all are
// confidently visible (> 0.6), otherwise null.
function visibleSide(landmarks, indexes) {
  const points = indexes.map((index) => landmarks[index]);
  if (points.some((point) => !point || (point.visibility ?? 0) <= 0.6)) return null;
  return {
    points,
    visibility: points.reduce((total, point) => total + point.visibility, 0) / points.length,
  };
}

// Pick whichever side of the body (left/right) the camera sees better.
function bestVisibleSide(landmarks, leftIndexes, rightIndexes) {
  const left = visibleSide(landmarks, leftIndexes);
  const right = visibleSide(landmarks, rightIndexes);
  if (!left) return right;
  if (!right) return left;
  return left.visibility >= right.visibility ? left : right;
}

// Simple state machine: a rep is counted when the joint angle goes past one
// threshold and then back past the other. The gap between thresholds
// (hysteresis) stops jitter around a single value from double-counting.
export class RepCounter {
  constructor(exerciseType) {
    if (!["squat", "curl"].includes(exerciseType)) {
      throw new Error("Rep counting supports squats and bicep curls only.");
    }
    this.exerciseType = exerciseType;
    this.stage = exerciseType === "curl" ? "down" : "up";
    this.repCount = 0;
  }

  update(landmarks) {
    // MediaPipe pose indices: 23/24 hip, 25/26 knee, 27/28 ankle,
    // 11/12 shoulder, 13/14 elbow, 15/16 wrist (left/right)
    const side = this.exerciseType === "squat"
      ? bestVisibleSide(landmarks, [23, 25, 27], [24, 26, 28])
      : bestVisibleSide(landmarks, [11, 13, 15], [12, 14, 16]);
    if (!side) return { angle: null, stage: this.stage, repCount: this.repCount };

    const [pointA, pointB, pointC] = side.points;
    const angle = calculateAngle(pointA, pointB, pointC);
    if (this.exerciseType === "squat") {
      // Squat: knee bends below 120 deg = down, straightens above 140 deg = rep done
      if (this.stage === "up" && angle < 120) this.stage = "down";
      else if (this.stage === "down" && angle > 140) {
        this.stage = "up";
        this.repCount += 1;
      }
    // Curl: elbow closes below 75 deg = up, extends above 135 deg = rep done
    } else if (this.stage === "down" && angle < 75) {
      this.stage = "up";
    } else if (this.stage === "up" && angle > 135) {
      this.stage = "down";
      this.repCount += 1;
    }
    return { angle, stage: this.stage, repCount: this.repCount };
  }
}
