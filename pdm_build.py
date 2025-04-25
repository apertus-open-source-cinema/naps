#!/usr/bin/env python3

import os
from pdm.backend.hooks.version import SCMVersion
from pdm.backend._vendor.packaging.version import Version

def format_version(version: SCMVersion) -> str:
    print(version.version)
    major, minor = (int(n) for n in str(version.version).split(".")[:3])
    if minor == 0:
        minor = 1
    if version.distance is None:
        return f"{major}.{minor}"
    else:
        return f"{major}.{minor}.dev{version.distance}"

def pdm_build_initialize(context):
    if "DOC_SHA" in os.environ:
        context.config.metadata["urls"]["Documentation"] = f"https://docs.niemo.de/naps/commit/{os.environ['DOC_SHA']}".strip()
    
    # we cannot depend on git dependencies for pypi so we filter out amaranth-boards as it is not published at the time I write this
    context.config.metadata["dependencies"] = [dep for dep in context.config.metadata["dependencies"] if "git" not in dep]
