"""
test_bbox_smoother.py — Unit Tests for the Smoothing & Crop Module
===================================================================

These tests verify the core logic of bbox_smoother.py without needing
any video files, FFmpeg, or MediaPipe.  Pure Python + NumPy only.

Run:
    cd backend
    python -m pytest tests/test_bbox_smoother.py -v
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

        # After 50 updates, should be very close to target
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

        # Variance of smoothed signal should be less than raw
        raw_var = sum((v - target) ** 2 for v in raw_values) / len(raw_values)
        smooth_var = sum((v - target) ** 2 for v in smoothed) / len(smoothed)

        assert smooth_var < raw_var, (
            f"Smoothed variance ({smooth_var:.1f}) should be < "
            f"raw variance ({raw_var:.1f})"
        )

    def test_predict_continues_motion(self):
        """Predict should extrapolate using estimated velocity."""
        kf = KalmanFilter1D()

        # Feed a linearly increasing sequence
        for i in range(20):
            kf.update(float(i * 10))

        # Predicted next position should be close to 200
        predicted = kf.predict()
        assert predicted > 180, f"Expected ~200, got {predicted}"

    def test_velocity_is_positive_for_increasing_signal(self):
        """Velocity should be positive when measurements increase."""
        kf = KalmanFilter1D()
        for i in range(20):
            kf.update(float(i * 5))
        assert kf.velocity > 0, f"Expected positive velocity, got {kf.velocity}"


# ═════════════════════════════════════════════════════════════
# 2. EMA FILTER TESTS
# ═════════════════════════════════════════════════════════════

class TestEMAFilter:
    """Tests for the Exponential Moving Average filter."""

    def test_first_value_is_exact(self):
        """First update should return the measurement exactly."""
        ema = EMAFilter(alpha=0.3)
        result = ema.update(42.0)
        assert result == 42.0

    def test_converges_to_constant(self):
        """Repeated constant measurements should converge."""
        ema = EMAFilter(alpha=0.2)
        for _ in range(100):
            result = ema.update(200.0)
        assert abs(result - 200.0) < 0.01

    def test_high_alpha_is_snappier(self):
        """Higher alpha should track changes faster."""
        ema_slow = EMAFilter(alpha=0.05)
        ema_fast = EMAFilter(alpha=0.9)

        # Start at 0
        ema_slow.update(0.0)
        ema_fast.update(0.0)

        # Jump to 100
        slow_result = ema_slow.update(100.0)
        fast_result = ema_fast.update(100.0)

        assert fast_result > slow_result, (
            f"Fast ({fast_result}) should be closer to 100 than slow ({slow_result})"
        )

    def test_low_alpha_is_smoother(self):
        """Lower alpha should produce smoother output."""
        import random
        random.seed(123)

        ema_smooth = EMAFilter(alpha=0.05)
        ema_rough = EMAFilter(alpha=0.8)

        values = [100 + random.gauss(0, 30) for _ in range(50)]
        smooth_results = [ema_smooth.update(v) for v in values]
        rough_results = [ema_rough.update(v) for v in values]

        # Calculate jitter (sum of absolute differences between consecutive values)
        smooth_jitter = sum(abs(smooth_results[i+1] - smooth_results[i]) for i in range(len(smooth_results)-1))
        rough_jitter = sum(abs(rough_results[i+1] - rough_results[i]) for i in range(len(rough_results)-1))

        assert smooth_jitter < rough_jitter


# ═════════════════════════════════════════════════════════════
# 3. BBOX SMOOTHER TESTS
# ═════════════════════════════════════════════════════════════

class TestBBoxSmoother:
    """Tests for the combined smoother wrapper."""

    def test_kalman_method_works(self):
        """BBoxSmoother with Kalman should return valid coordinates."""
        smoother = BBoxSmoother(method="kalman")
        cx, cy = smoother.update((960, 540), 1920, 1080)
        assert 0 <= cx <= 1920
        assert 0 <= cy <= 1080

    def test_ema_method_works(self):
        """BBoxSmoother with EMA should return valid coordinates."""
        smoother = BBoxSmoother(method="ema")
        cx, cy = smoother.update((960, 540), 1920, 1080)
        assert 0 <= cx <= 1920
        assert 0 <= cy <= 1080

    def test_no_face_freezes_position(self):
        """When face disappears, position should stay near last known."""
        smoother = BBoxSmoother(method="kalman")

        # Feed several frames with a face
        for _ in range(10):
            smoother.update((500, 300), 1920, 1080)

        # Now send None (no face)
        cx, cy = smoother.update(None, 1920, 1080)

        # Should be near (500, 300), not jumping to centre
        assert abs(cx - 500) < 50, f"Expected ~500, got {cx}"
        assert abs(cy - 300) < 50, f"Expected ~300, got {cy}"

    def test_invalid_method_raises(self):
        """Invalid method should raise ValueError."""
        try:
            BBoxSmoother(method="invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


# ═════════════════════════════════════════════════════════════
# 4. CROP WINDOW CALCULATOR TESTS
# ═════════════════════════════════════════════════════════════

class TestCropWindowCalculator:
    """Tests for the 9:16 crop window calculator."""

    def test_standard_1920x1080(self):
        """Standard 16:9 source should produce a valid 9:16 crop."""
        calc = CropWindowCalculator(1920, 1080)

        # Width should be 1080 * 9/16 = 607.5 → 606 (even)
        assert calc.crop_h == 1080
        assert calc.crop_w % 2 == 0  # must be even
        assert calc.crop_w < 1920    # must fit in frame

        # Check aspect ratio is approximately 9:16
        ratio = calc.crop_w / calc.crop_h
        assert abs(ratio - 9/16) < 0.01

    def test_crop_centred_on_face(self):
        """Crop should be centred on the given coordinates."""
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(960.0, 540.0)  # frame centre

        # Should be centred
        crop_cx = crop.x + crop.width / 2
        crop_cy = crop.y + crop.height / 2
        assert abs(crop_cx - 960) < 2
        assert abs(crop_cy - 540) < 2

    def test_crop_clamped_left_edge(self):
        """Crop near left edge should be clamped (x >= 0)."""
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(0.0, 540.0)

        assert crop.x >= 0, f"x should be >= 0, got {crop.x}"
        assert crop.x + crop.width <= 1920

    def test_crop_clamped_right_edge(self):
        """Crop near right edge should be clamped."""
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(1920.0, 540.0)

        assert crop.x >= 0
        assert crop.x + crop.width <= 1920, (
            f"Crop extends past frame: x={crop.x}, w={crop.width}"
        )

    def test_crop_clamped_top_edge(self):
        """Crop near top should be clamped (y >= 0)."""
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(960.0, 0.0)

        assert crop.y >= 0
        assert crop.y + crop.height <= 1080

    def test_crop_clamped_bottom_edge(self):
        """Crop near bottom should be clamped."""
        calc = CropWindowCalculator(1920, 1080)
        crop = calc.compute(960.0, 1080.0)

        assert crop.y >= 0
        assert crop.y + crop.height <= 1080

    def test_dimensions_are_even(self):
        """Crop dimensions must be even (codec requirement)."""
        # Test with an unusual source resolution
        calc = CropWindowCalculator(1280, 721)
        assert calc.crop_w % 2 == 0
        assert calc.crop_h % 2 == 0

    def test_crop_window_never_exceeds_frame(self):
        """No matter where the face is, crop must stay inside frame."""
        calc = CropWindowCalculator(1920, 1080)

        # Test many positions including corners and edges
        test_positions = [
            (0, 0), (1920, 0), (0, 1080), (1920, 1080),
            (960, 540), (100, 100), (1800, 900),
            (-100, -100), (5000, 5000),
        ]

        for cx, cy in test_positions:
            crop = calc.compute(float(cx), float(cy))
            assert crop.x >= 0, f"x < 0 for ({cx}, {cy})"
            assert crop.y >= 0, f"y < 0 for ({cx}, {cy})"
            assert crop.x + crop.width <= 1920, f"Right edge overflow for ({cx}, {cy})"
            assert crop.y + crop.height <= 1080, f"Bottom edge overflow for ({cx}, {cy})"


# ═════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Run all tests manually if pytest is not available."""
    test_classes = [
        TestKalmanFilter1D,
        TestEMAFilter,
        TestBBoxSmoother,
        TestCropWindowCalculator,
    ]

    total = 0
    passed = 0
    failed = 0

    for cls in test_classes:
        print(f"\n{'='*60}")
        print(f"  {cls.__name__}")
        print(f"{'='*60}")

        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            total += 1
            try:
                getattr(instance, method_name)()
                print(f"  ✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
                failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
