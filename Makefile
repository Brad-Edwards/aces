.PHONY: policy

policy:
	uv tool run --from 'nox[uv]==2026.4.10' nox -f noxfile.py -s policy
