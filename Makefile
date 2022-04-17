
.PHONY: run
run: cozmo_ar.py
	cat cmds.py - | simple_cli

cozmo_ar.py: cozmo_ar.fsm
	genfsm cozmo_ar.fsm
