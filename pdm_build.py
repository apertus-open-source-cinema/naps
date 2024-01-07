#!/usr/bin/env python3

import os

def pdm_build_initialize(context):
    if "DOC_SHA" in os.environ:
        context.config.metadata["urls"]["Documentation"] = f"https://docs.niemo.de/naps/commit/{os.environ['DOC_SHA']}".strip()
