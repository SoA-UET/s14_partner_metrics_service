from flask import Flask

from .v1 import v1

def register_api_controllers(app: Flask):
    """Register all API blueprints with the Flask app."""
    app.register_blueprint(v1)

    @app.get('/api', strict_slashes=False)
    def get_api_versions():
        links = "".join(
            build_api_version_doc_link(api_version) for api_version in API_VERSIONS
        )
        return f"""
        <html><head><title>API Documentation</title></head><body>
        <h1>API Documentation</h1>
        <div>
            <p>Here are all versions of the API, along with their respective documentation.</p>

            <ul>{links}</ul>
        </div>
        </body></html>
        """
