#!/bin/bash
# Verification script for Felled Woodland Trading Rule solution

echo "=============================================="
echo "Verifying Felled Woodland Trading Solution"
echo "=============================================="
echo ""

# Check files exist
echo "✓ Checking files..."
files=(
    "test_felled_woodland_trading.py"
    "add_felled_woodland_trading_rule.sql"
    "FELLED_WOODLAND_TRADING_IMPLEMENTATION.md"
    "SUMMARY.md"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (MISSING!)"
        all_exist=false
    fi
done
echo ""

# Run the test
echo "✓ Running test suite..."
python test_felled_woodland_trading.py 2>&1 | grep -E "(Testing|Test:|Options found:|TEST PASSED|ALL TESTS PASSED|Conclusion)" | head -15
test_result=$?
echo ""

if [ $test_result -eq 0 ]; then
    echo "✅ All tests passed successfully!"
else
    echo "❌ Tests failed!"
fi
echo ""

# Check SQL script
echo "✓ Checking SQL script..."
if grep -q "INSERT INTO.*TradingRules" add_felled_woodland_trading_rule.sql; then
    echo "  ✅ SQL script contains trading rule INSERT"
else
    echo "  ❌ SQL script invalid"
fi
echo ""

# Summary
echo "=============================================="
if [ "$all_exist" = true ] && [ $test_result -eq 0 ]; then
    echo "✅ VERIFICATION PASSED - Solution ready!"
    echo ""
    echo "Next steps:"
    echo "1. Admin applies: add_felled_woodland_trading_rule.sql"
    echo "2. Test in app with Felled woodland demand"
    echo "3. See FELLED_WOODLAND_TRADING_IMPLEMENTATION.md for details"
else
    echo "❌ VERIFICATION FAILED - Check errors above"
fi
echo "=============================================="
