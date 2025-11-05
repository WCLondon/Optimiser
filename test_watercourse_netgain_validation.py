"""
Test to verify that Net Gain (Watercourses) is accepted in validation.
This tests the fix for the issue where "Net Gain (Watercourses)" was being
rejected with the error: "These demand habitats aren't in the catalog"
"""

def test_net_gain_labels_defined():
    """Test that all three Net Gain labels are defined in app.py"""
    with open("app.py", "r") as f:
        content = f.read()
    
    # Check that all three Net Gain labels are defined
    assert 'NET_GAIN_LABEL = "Net Gain (Low-equivalent)"' in content, \
        "NET_GAIN_LABEL should be defined"
    assert 'NET_GAIN_HEDGEROW_LABEL = "Net Gain (Hedgerows)"' in content, \
        "NET_GAIN_HEDGEROW_LABEL should be defined"
    assert 'NET_GAIN_WATERCOURSE_LABEL = "Net Gain (Watercourses)"' in content, \
        "NET_GAIN_WATERCOURSE_LABEL should be defined"
    
    print("✅ All three Net Gain labels are defined")
    return True


def test_validation_includes_all_net_gain_labels():
    """Test that the validation check includes all three Net Gain labels"""
    with open("app.py", "r") as f:
        content = f.read()
    
    # Find the validation line
    validation_line = None
    for line in content.split('\n'):
        if 'unknown = [h for h in demand_df["habitat_name"]' in line:
            validation_line = line
            break
    
    assert validation_line is not None, "Validation line not found"
    
    # Check that all three Net Gain labels are in the validation exception list
    assert "NET_GAIN_LABEL" in validation_line, \
        "NET_GAIN_LABEL should be in validation exception list"
    assert "NET_GAIN_HEDGEROW_LABEL" in validation_line, \
        "NET_GAIN_HEDGEROW_LABEL should be in validation exception list"
    assert "NET_GAIN_WATERCOURSE_LABEL" in validation_line, \
        "NET_GAIN_WATERCOURSE_LABEL should be in validation exception list"
    
    print("✅ Validation check includes all three Net Gain labels")
    print(f"   Validation line: {validation_line.strip()}")
    return True


def test_watercourse_net_gain_in_hab_choices():
    """Test that NET_GAIN_WATERCOURSE_LABEL is in HAB_CHOICES"""
    with open("app.py", "r") as f:
        content = f.read()
    
    # Find the HAB_CHOICES definition
    in_hab_choices = False
    for line in content.split('\n'):
        if 'HAB_CHOICES = sorted(' in line:
            in_hab_choices = True
        if in_hab_choices and 'NET_GAIN_WATERCOURSE_LABEL' in line:
            print("✅ NET_GAIN_WATERCOURSE_LABEL is included in HAB_CHOICES")
            return True
        if in_hab_choices and line.strip() and not line.strip().startswith((')', ']', '+')):
            continue
        if in_hab_choices and line.strip().startswith(')') and 'NET_GAIN_WATERCOURSE_LABEL' not in line:
            # Check if it's on the next line
            continue
    
    # Also check if it's added separately
    if 'NET_GAIN_WATERCOURSE_LABEL' in content[content.find('HAB_CHOICES'):content.find('HAB_CHOICES')+500]:
        print("✅ NET_GAIN_WATERCOURSE_LABEL is included in HAB_CHOICES")
        return True
    
    raise AssertionError("NET_GAIN_WATERCOURSE_LABEL not found in HAB_CHOICES")


def test_get_umbrella_for_handles_watercourse():
    """Test that get_umbrella_for function handles NET_GAIN_WATERCOURSE_LABEL"""
    with open("app.py", "r") as f:
        content = f.read()
    
    # Find the get_umbrella_for function
    umbrella_func_start = content.find("def get_umbrella_for(")
    assert umbrella_func_start > 0, "get_umbrella_for function not found"
    
    # Get the function content (next 500 chars should be enough)
    func_content = content[umbrella_func_start:umbrella_func_start+500]
    
    # Check it handles NET_GAIN_WATERCOURSE_LABEL
    assert "NET_GAIN_WATERCOURSE_LABEL" in func_content, \
        "get_umbrella_for should handle NET_GAIN_WATERCOURSE_LABEL"
    assert "LEDGER_WATER" in func_content or "watercourse" in func_content.lower(), \
        "get_umbrella_for should return watercourse ledger for NET_GAIN_WATERCOURSE_LABEL"
    
    print("✅ get_umbrella_for function handles NET_GAIN_WATERCOURSE_LABEL")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Net Gain (Watercourses) Validation Fix")
    print("=" * 60)
    
    tests = [
        test_net_gain_labels_defined,
        test_validation_includes_all_net_gain_labels,
        test_watercourse_net_gain_in_hab_choices,
        test_get_umbrella_for_handles_watercourse,
    ]
    
    all_passed = True
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {test.__name__} errored: {e}")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
        exit(1)
    print("=" * 60)
