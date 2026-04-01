# -*- coding: utf-8 -*-
"""
run_single.py

Description
-----------
Runs vertical structure analysis for a single date and single time window, with settings defined in 
vertical_structure_src/vertical_structure_config.py.
"""

import vertical_structure_src.vertical_structure_main as vs_main

if __name__ == "__main__":
    print ("\n Running analysis in 'single' mode: a single date and time window...")
    vs_main.main()