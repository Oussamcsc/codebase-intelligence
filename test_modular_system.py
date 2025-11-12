#!/usr/bin/env python3
"""
Quick test of the modular code review system
"""

def test_function():
    """Test function for code review"""
    x = 5  # Magic number
    try:
        result = eval("x + 1")  # Dangerous eval
    except:  # Bare except
        pass
    
    # Unused variable
    unused_var = "hello"
    
    return result

def another_function():
    """Another test function"""
    global global_var
    global_var = "test"  # Global assignment
    
    # Nested loops for complexity
    for i in range(5):
        for j in range(5):
            for k in range(5):
                for l in range(5):  # 4 levels deep
                    print(i, j, k, l)

# No type hints anywhere
def bad_function(param):
    return param * 2

# Duplicate of above  
def duplicate_function(param):
    return param * 2

if __name__ == "__main__":
    test_function()
    another_function()
    bad_function(5)