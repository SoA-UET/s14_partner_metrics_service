# Controllers module - routes are registered directly in __main__.py

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
