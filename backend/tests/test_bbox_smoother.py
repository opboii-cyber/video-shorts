"""
test_bbox_smoother.py — Unit Tests for the Smoothing & Crop Module
===================================================================

These tests verify the core logic of bbox_smoother.py without needing
any video files, FFmpeg, or MediaPipe.  Pure Python + NumPy only.

Run:
    cd backend
    python -m pytest tests/test_bbox_smoother.py -v
    # or without pytest:
    python tests/test_bbox_smoother.py
"""

import sys
import os

# Add backend to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bbox_smoother import (
    KalmanFilter1D,
    EMAFilter,
    BBoxSmoother,
    CropWindowCalculator,
    CropWindow,
)


# ═════════════════════════════════════════════════════════════
# 1. KALMAN FILTER TESTS
# ═════════════════════════════════════════════════════════════

class TestKalmanFilter1D:
    """Tests for the 1-D Kalman filter."""

    def test_initialisation_snaps_to_first_measurement(self):
        """First update should return the measurement exactly."""
        kf = KalmanFilter1D()
        result = kf.update(100.0)
        assert result == 100.0, f"Expected 100.0, got {result}"

    def test_converges_to_constant_target(self):
        """Repeated measurements at same position should converge."""
        kf = KalmanFilter1D()
        target = 500.0

        for _ in range(50):
            result = kf.update(target)

        assert abs(result - target) < 1.0, f"Expected ~{target}, got {result}"

    def test_smooths_noisy_signal(self):
        """A noisy signal should be smoothed (less variance)."""
        import random
        random.seed(42)

        kf = KalmanFilter1D()
        target = 300.0
        noise_std = 50.0

        raw_values = [target + random.gauss(0, noise_std) for _ in range(100)]
        smoothed = [kf.update(v) for v in raw_values]

        raw_var = sum((v - target) ** 2 for v in raw_values) / len(raw_values)
        smooth_var = sum((v - target) ** 2 for v in smoothed) / len(smoothed)

        assert smooth_var < raw_var

    def test_predict_continues_motion(self):
        """Predict should extrapolate using estimated velocity."""
        kf = KalmanFilter1D()
        for i in range(20):
            kf.update(float(i * 10))
        predicted = kf.predict()
        assert predicted > 180, f"Expected ~200, got {predicted}"

    def test_velocity_is_positive_for_increasing_signal(self):
        """Velocity should be positive when measurements increase."""
        kf = KalmanFilter1D()
        for i in range(20):
            kf.update(float(i * 5))
        assert kf.velocity > 0


# ═════════════════════════════════════════════════════════════
# 2. EMA FILTER TESTS
# ═════════════════════════════════════════════════════════════

class TestEMAFilter:

    def test_first_value_is_exact(self):
        ema = EMAFilter(alpha=0.3)
        assert ema.update(42.0) == 42.0

    def test_converges_to_constant(self):
        ema = EMAFilter(alpha=0.2)
        for _ in range(100):
            result = ema.update(200.0)
        assert abs(result - 200.0) < 0.01

    def test_high_alpha_is_snappier(self):
        ema_slow = EMAFilter(alpha=0.05)
        ema_fast = EMAFilter(alpha=0.9)
        ema_slow.update(0.0)
        ema_fast.update(0.0)
        slow_result = ema_slow.update(100.0)
        fast_result = ema_fast.update(100.0)
        assert fast_result > slow_result


# ═════════════════════════════════════════════════════════════
# 3. BBOX SMOOTHER TESTS
# ═════════════════════════════════════════════════════════════

class TestBBoxSmoother:

    def test_kalman_method_works(self):
        smoother = BBoxSmoother(method="kalman")
        cx, cy = smoother.update((960, 540), 1920, 1080)
        assert 0 <= cx <= 1920
        assert 0 <= cy <= 1080

    def test_ema_method_works(self):
        smoother = BBoxSmoother(method="ema")
        cx, cy = smoother.update((960, 540), 1920, 1080)
        assert 0 <= cx <= 1920
        assert 0 <= cy <= 1080

    def test_no_face_freezes_position(self):
        smoother = BBoxSmoother(method="kalman")
        for _ in range(10):
            smoother.update((500, 300), 1920, 1080)
        cx, cy = smoother.update(None, 1920, 1080)
        assert abs(cx - 500) < 50
        assert abs(cy - 300) < 50

    def test_invalid_method_raises(self):
        try:
            BBoxSmoother(method="invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


# ═════════════════════════════════════════════════════════════
# 4. CROP WINDOW CALCULATOR TESTS
# ═════════════════════════════════════════════════════════════

class TestCropWindowCalculator:

    def test_standard_1920x1080(self):
        calc = CropWindowCalculator(1920, 1080)
        assert calc.crop_h == 1080
        assert calc.crop_w % 2 == 0
        assert calc.crop_w < 1920
        ratio = calc.crop_w / calc.crop_h
        assert abs(ratio - 9/16) < 0.01

    def test_crop_centred_on_face(self):
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(960.0, 540.0)
        crop_cx = crop.x + crop.width / 2
        crop_cy = crop.y + crop.height / 2
        assert abs(crop_cx - 960) < 2
        assert abs(crop_cy - 540) < 2

    def test_crop_clamped_left_edge(self):
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(0.0, 540.0)
        assert crop.x >= 0
        assert crop.x + crop.width <= 1920

    def test_crop_clamped_right_edge(self):
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(1920.0, 540.0)
        assert crop.x >= 0
        assert crop.x + crop.width <= 1920

    def test_crop_never_exceeds_frame(self):
        calc = CropWindowCalculator(1920, 1080)
        for cx, cy in [(0,0), (1920,0), (0,1080), (1920,1080), (960,540), (-100,-100), (5000,5000)]:
            crop = calc.compute(float(cx), float(cy))
            assert crop.x >= 0
            assert crop.y >= 0
            assert crop.x + crop.width <= 1920
            assert crop.y + crop.height <= 1080

    def test_dimensions_are_even(self):
        calc = CropWindowCalculator(1280, 721)
        assert calc.crop_w % 2 == 0
        assert calc.crop_h % 2 == 0


# ═════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_classes = [TestKalmanFilter1D, TestEMAFilter, TestBBoxSmoother, TestCropWindowCalculator]
    total = passed = failed = 0

    for cls in test_classes:
        print(f"\n{'='*60}\n  {cls.__name__}\n{'='*60}")
        instance = cls()
        for m in [m for m in dir(instance) if m.startswith("test_")]:
            total += 1
            try:
                getattr(instance, m)()
                print(f"  ✓ {m}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {m}: {e}")
                failed += 1

    print(f"\n{'='*60}\n  Results: {passed}/{total} passed, {failed} failed\n{'='*60}")
