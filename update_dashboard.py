import re

with open('dashboard.py', 'r') as f:
    content = f.read()

# Add import for subprocess at the top
if 'import subprocess' not in content:
    content = content.replace('from flask import Flask', 'from flask import Flask\nimport subprocess\nimport sys')

# Add route for generating predictions (before if __name__)
new_route = '''
@app.route('/generate')
def generate_predictions():
    """Generate fresh predictions"""
    try:
        # Run update and predict
        subprocess.run([sys.executable, 'main.py', 'update'], check=True, timeout=120)
        subprocess.run([sys.executable, 'main.py', 'predict'], check=True, timeout=60)
        return {'status': 'success', 'message': 'Predictions generated!'}
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'Timeout - this takes a while on Render'}, 500
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

'''

# Insert before if __name__
if '@app.route(\'/generate\')' not in content:
    content = content.replace('\nif __name__ == \'__main__\':', new_route + '\nif __name__ == \'__main__\':')

with open('dashboard.py', 'w') as f:
    f.write(content)

print("✓ Updated dashboard.py")
