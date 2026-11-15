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
  const cosine = Math.max(-1, Math.min(1, dotProduct / (magnitudeBA * magnitudeBC)));
  return Math.acos(cosine) * (180 / Math.PI);
}

export function supportedExerciseType(name) {
  if (/\bsquats?\b/i.test(name)) return "squat";
  if (/\bbicep curls?\b/i.test(name)) return "curl";
  return null;
}

function visibleSide(landmarks, indexes) {
  const points = indexes.map((index) => landmarks[index]);
  if (points.some((point) => !point || (point.visibility ?? 0) <= 0.6)) return null;
  return {
    points,
    visibility: points.reduce((total, point) => total + point.visibility, 0) / points.length,
  };
}

function bestVisibleSide(landmarks, leftIndexes, rightIndexes) {
  const left = visibleSide(landmarks, leftIndexes);
  const right = visibleSide(landmarks, rightIndexes);
  if (!left) return right;
  if (!right) return left;
  return left.visibility >= right.visibility ? left : right;
}

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
    const side = this.exerciseType === "squat"
      ? bestVisibleSide(landmarks, [23, 25, 27], [24, 26, 28])
      : bestVisibleSide(landmarks, [11, 13, 15], [12, 14, 16]);
    if (!side) return { angle: null, stage: this.stage, repCount: this.repCount };

    const [pointA, pointB, pointC] = side.points;
    const angle = calculateAngle(pointA, pointB, pointC);
    if (this.exerciseType === "squat") {
      if (this.stage === "up" && angle < 120) this.stage = "down";
      else if (this.stage === "down" && angle > 140) {
        this.stage = "up";
        this.repCount += 1;
      }
    } else if (this.stage === "down" && angle < 75) {
      this.stage = "up";
    } else if (this.stage === "up" && angle > 135) {
      this.stage = "down";
      this.repCount += 1;
    }
    return { angle, stage: this.stage, repCount: this.repCount };
  }
}
