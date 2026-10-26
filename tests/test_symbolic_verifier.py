"""
Test Suite for Symbolic IR Verifier Engine (Z3 SMT Solver)
Validates mathematical equivalence, counterexample generation, and poison handling.
"""

import pytest
from engine.symbolic_verifier import (
    SymbolicIRVerifier,
    VerificationVerdict,
    verify_ir_equivalence,
)


class TestSymbolicVerifier:
    """Tests for pure SMT-based LLVM IR symbolic translation validation"""

    def test_identity_equivalence(self):
        """Source and target are identical functions -> PROVED"""
        ir = """
define i32 @identity(i32 %x) {
  ret i32 %x
}
"""
        report = verify_ir_equivalence(ir, ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True
        assert report.functions_checked == 1

    def test_distributive_law(self):
        """2*(x + y) == 2*x + 2*y -> PROVED"""
        orig = """
define i32 @distrib(i32 %x, i32 %y) {
  %1 = add i32 %x, %y
  %2 = mul i32 %1, 2
  ret i32 %2
}
"""
        opt = """
define i32 @distrib(i32 %x, i32 %y) {
  %1 = mul i32 %x, 2
  %2 = mul i32 %y, 2
  %3 = add i32 %1, %2
  ret i32 %3
}
"""
        report = verify_ir_equivalence(orig, opt)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_strength_reduction_equivalence(self):
        """x * 2 == x << 1 -> PROVED"""
        orig = """
define i32 @shl_opt(i32 %x) {
  %1 = mul i32 %x, 2
  ret i32 %1
}
"""
        opt = """
define i32 @shl_opt(i32 %x) {
  %1 = shl i32 %x, 1
  ret i32 %1
}
"""
        report = verify_ir_equivalence(orig, opt)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_arithmetic_mutation_failure(self):
        """x + y != x - y -> FAILED with counterexample"""
        orig = """
define i32 @compute(i32 %a, i32 %b) {
  %res = add i32 %a, %b
  ret i32 %res
}
"""
        mutated = """
define i32 @compute(i32 %a, i32 %b) {
  %res = sub i32 %a, %b
  ret i32 %res
}
"""
        report = verify_ir_equivalence(orig, mutated)
        assert report.verdict == VerificationVerdict.FAILED
        assert report.proved is False
        assert report.counterexample is not None
        assert "Example:" in report.output
        assert "1 incorrect transformation" in report.output

    def test_dropped_nsw_flag_poison(self):
        """Target drops 'nsw' flag on signed add -> FAILED with overflow counterexample"""
        orig = """
define i32 @safe_add(i32 %a, i32 %b) {
  %res = add nsw i32 %a, %b
  ret i32 %res
}
"""
        opt = """
define i32 @safe_add(i32 %a, i32 %b) {
  %res = add i32 %a, %b
  ret i32 %res
}
"""
        report = verify_ir_equivalence(orig, opt)
        assert report.verdict == VerificationVerdict.FAILED
        assert report.proved is False
        assert report.counterexample is not None
        assert "dropped nsw" in report.counterexample.failure_reason.lower() or "more undefined" in report.counterexample.failure_reason.lower()

    def test_bitcast_and_trunc(self):
        """Bitwise extraction trunc i64 to i32 -> PROVED"""
        orig = """
define i32 @truncate(i64 %x) {
  %1 = trunc i64 %x to i32
  ret i32 %1
}
"""
        report = verify_ir_equivalence(orig, orig)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_mem2reg_alloca_store_load_equivalence(self):
        """Unoptimized stack-allocated IR is equivalent to register-promoted IR -> PROVED"""
        unoptimized = """
define i32 @add(i32 %0, i32 %1) {
  %3 = alloca i32, align 4
  %4 = alloca i32, align 4
  store i32 %0, ptr %3, align 4
  store i32 %1, ptr %4, align 4
  %5 = load i32, ptr %3, align 4
  %6 = load i32, ptr %4, align 4
  %7 = add i32 %5, %6
  ret i32 %7
}
"""
        optimized = """
define i32 @add(i32 %a, i32 %b) {
  %res = add i32 %a, %b
  ret i32 %res
}
"""
        report = verify_ir_equivalence(unoptimized, optimized)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True
        assert report.functions_checked == 1

    def test_select_instruction_min(self):
        """Branchless min with icmp and select -> PROVED"""
        orig = """
define i32 @min_val(i32 %a, i32 %b) {
  %cmp = icmp slt i32 %a, %b
  %res = select i1 %cmp, i32 %a, i32 %b
  ret i32 %res
}
"""
        # Identical or commutated
        opt = """
define i32 @min_val(i32 %x, i32 %y) {
  %cmp = icmp slt i32 %x, %y
  %res = select i1 %cmp, i32 %x, i32 %y
  ret i32 %res
}
"""
        report = verify_ir_equivalence(orig, opt)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_phi_to_select_equivalence(self):
        """CFG diamond branch with phi node is equivalent to select instruction -> PROVED"""
        branching_cfg = """
define i32 @abs_val(i32 %x) {
entry:
  %cmp = icmp slt i32 %x, 0
  br i1 %cmp, label %then, label %else
then:
  %neg = sub i32 0, %x
  br label %merge
else:
  br label %merge
merge:
  %res = phi i32 [ %neg, %then ], [ %x, %else ]
  ret i32 %res
}
"""
        branchless_select = """
define i32 @abs_val(i32 %x) {
  %cmp = icmp slt i32 %x, 0
  %neg = sub i32 0, %x
  %res = select i1 %cmp, i32 %neg, i32 %x
  ret i32 %res
}
"""
        report = verify_ir_equivalence(branching_cfg, branchless_select)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_memcpy_symbolic_equivalence(self):
        """Block memory copy (@llvm.memcpy) is proved equivalent to direct value return."""
        orig_ir = """
define i32 @test_copy(i32 %val) {
entry:
    %src = alloca i32, align 4
    %dst = alloca i32, align 4
    store i32 %val, ptr %src, align 4
    call void @llvm.memcpy.p0.p0.i64(ptr %dst, ptr %src, i64 4, i1 false)
    %loaded = load i32, ptr %dst, align 4
    ret i32 %loaded
}
"""
        opt_ir = """
define i32 @test_copy(i32 %val) {
entry:
    ret i32 %val
}
"""
        report = verify_ir_equivalence(orig_ir, opt_ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True

    def test_memset_symbolic_equivalence(self):
        """Block memory zeroization (@llvm.memset) is proved equivalent to constant zero return."""
        orig_ir = """
define i32 @test_zero() {
entry:
    %buf = alloca i32, align 4
    call void @llvm.memset.p0.i64(ptr %buf, i8 0, i64 4, i1 false)
    %res = load i32, ptr %buf, align 4
    ret i32 %res
}
"""
        opt_ir = """
define i32 @test_zero() {
entry:
    ret i32 0
}
"""
        report = verify_ir_equivalence(orig_ir, opt_ir)
        assert report.verdict == VerificationVerdict.PROVED
        assert report.proved is True
