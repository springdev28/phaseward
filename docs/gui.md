# Local Phaseward control panel

Phaseward is in `/Users/baharyuksel/Documents/ChatGPT/Phaseward`; it is not an
application in macOS Applications. Its optional interface is a local browser
panel served by your Python environment. No account, external API, cloud service,
Docker, GPU, or physical device is involved. Initial package installation needs
a download; running the installed software does not.

## Install and start

From Terminal:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
pip install '.[dev,gui]'
streamlit run app.py
```

Open `http://127.0.0.1:8501`. Keep Terminal running. Stop with Ctrl+C. If starting
from scratch, first run `python3 -m venv .venv`. A working editable environment
can instead use `pip install -e '.[dev,gui]'`; this workspace previously needed a
regular wheel because of a hidden `.pth` import issue. Verify the imported
package after changes, then rebuild/reinstall as described in validation notes.

Always launch from the repository root: Streamlit reads `.streamlit/config.toml`
relative to the working directory. It binds only `127.0.0.1`, disables usage
statistics and file watching, retains CORS/XSRF protection, and uses bundled
fonts without remote assets. The panel refuses to run if launch overrides enable
usage statistics or replace the loopback address. The minimal toolbar hides
deployment controls. Do not launch the panel with remote-sharing flags.
Streamlit is an optional extra, currently tested with 1.67.0. CLI-only installs
do not import it, including when executing the numerical workflows.

## Four views

1. **Device Builder** samples bounded Gaussian gate shapes and their sum. Gray
   buffers lie outside the gated channel. Moving controls redraws geometry only;
   **Save device preview** records the arrays and plots without claiming a
   scattering result. Default coefficients are potential energies in meV.
   Voltage entry requires a nonzero signed coefficient α in meV/mV and records
   the illustrative assumption `u_j = α voltage_j`. This is not an electrostatic
   calibration, universal material constant, or electrode field solver. Gate
   widths are L/15, taper widths L/12, centers are specified relative to L, and
   the solver domain is [−2L/3, 2L/3]. Gates vanish outside [−L/2, L/2].
2. **Wave & Scattering Explorer** calls the existing stationary and packet
   runners. It displays T, R, complex transmission phase, spectral densities,
   packet probability, raw conditional fidelity and bounded delay alignment.
   The target is free propagation with identical mass, leads and phase planes.
   The library's lead reconstruction uses the exact discrete group velocity
   and energy Jacobian; |Ψ|² is probability density in nm⁻¹. Incoming t=0 and
   outgoing t=the recorded observation time are separate asymptotic components,
   not the full state inside the device or a classical trajectory. No display
   window normalization is applied. Review the finite-window probabilities and
   coarse/fine density differences before interpreting a reconstructed shape.
3. **Disorder Lab** calls the existing covariance and sensitivity runners with
   seed and seed+1 for separate preview checks. It displays representative full
   and KL samples, covariance checks, eigenmodes, complex derivatives, step
   convergence, and measured Taylor error separately from KL truncation error.
   ΦᵀWΦ=I, Var(ηₖ)=λₖ, δV=Φη. Neither shapes nor derivatives receive a second
   eigenvalue factor. These preview seeds are not optimization partitions.
4. **Optimization & Experiments** runs unmodified prespecified suites by
   default. Preview controls do not silently change them. The user may explicitly
   choose a custom preview-device suite or import a complete experiment JSON.
   Case overrides and convergence levels remain visible. Training, validation,
   held-out, initialization, bootstrap and convergence seeds are validated
   before a run. Designs freeze before evaluation draws are generated. The slower
   research profile requires a separate opt-in. Common held-out distributions,
   constraint residuals, failures, costs, convergence and uncertainty intervals
   remain visible, including unfavorable sensitivity comparisons.

Hover the question-mark tooltips for probability/amplitude, integral,
derivative, covariance, bandwidth, mass, target fidelity and delay explanations.

## Preview versus research

Preview controls are exploratory. The default window is
`[max(0.2, E0 − 4.5 σE), E0 + 4.5 σE]` meV; the Gaussian is restricted and
renormalized on this recorded finite window. Bandwidth means the untruncated
probability-density standard deviation. The exact lower/upper bounds, sampled
potential, grid, target, delay interval [−0.1,+0.1] ps, and all reconstruction
settings are included in the exported active configuration. Unsupported lead
bands, unresolved quadrature, invalid bounds and excessive dimensions are errors;
the panel does not silently replace the grid or model. A larger disorder-mode
count may fail if the numerical covariance has insufficient rank.

Gate energy bounds are ±25 meV individually; the absolute summed gate potential
is bounded by 60 meV at the sampled nodes. Optional voltage input uses those
same energy bounds after conversion. A pure geometry preview includes no
random draws even though its UI configuration retains the preview seed.

Changing a slider does not recompute existing scientific data. A result remains
bound to its own complete configuration and displays a stale-settings warning
when the draft changes. Use **Export active configuration** to export the draft;
use **Result configuration** to export the settings that actually produced the
displayed result. Import an exported preview through the sidebar. A full panel
preview JSON wraps ordinary CLI packet/disorder/sensitivity configurations in
named fields; only the corresponding inner configuration is passed to those
CLI commands. `examples/gui_preview.json` is an importable panel example.

## Local jobs and cancellation

Only explicit Run/Save actions start work. Each browser session owns at most
one subprocess, with the same Python interpreter/package origin and BLAS thread
caps set to one. A stage log and elapsed time are displayed; there is no invented
percent-complete estimate. The Cancel control sends SIGINT to that owned child,
then termination after three seconds and kill after five seconds if it has not
exited. Cancellation is cooperative where the underlying code permits it; an
uninterruptible library call can delay handling. Partial files are retained and
never cached as successful results. A forced stop may leave no final manifest;
`job_status.json` and `worker.log` explain the incomplete output.

Closing/reloading a tab does not forcibly stop an already launched subprocess.
Wait for completion or cancel before closing. Finished results can be reopened
from disk. Two browser sessions can each run a worker; the one-worker limit is
per session, not a global operating-system quota. Avoid launching several heavy
research runs on a laptop at once.

Jobs are stored in `results/gui-jobs/<UTC timestamp>-<unique id>/` with request,
log, status and a `result/` bundle. Directories are never silently overwritten.
Exact preview cache keys hash all resolved settings (including seeds, units,
voltage mapping, reconstruction settings and operation), source hashes, package
versions and hardware metadata. A hit reopens the original timestamped bundle
after verifying hashes. Research suites always create a new run and never use
the preview cache. Replaying identical research seeds is not fresh evidence.

## Open and export results

Choose **Open saved results**, select a folder below this workspace's `results/`,
then **Open result**. This verifies original output hashes and displays saved
arrays, figures, diagnostics, raw trials and reports without any solver call.
The displayed scope, status and timestamp are those of the opened run; selecting
a different folder does not implicitly open it. Legacy manifests have no
explicit success status: inspect their metrics. Failed checks are not hidden.

The export section offers the recorded configuration, a self-contained manifest,
underlying JSON/CSV/NPZ, PNG/SVG/PDF plots, and a complete portable ZIP. The latter
preserves the full file inventory and hashes. Data-only and plot-only ZIPs are
subsets; their manifest still describes the complete run. New panel manifests
embed the original component manifests with equations/approximations, parameters,
seeds, source identity, software versions and CPU environment. Saved reports are
rendered as text so an imported report cannot fetch a remote image.

The reader rejects traversal paths, symbolic links and modified artifacts. NPZ
uses `allow_pickle=False`. Runs and expanded NPZ archives above 256 MiB are
refused by the panel to bound laptop memory; use the CLI/filesystem for those.
No result is automatically repaired or recomputed. Incomplete directories
without a manifest are not shown in the result picker.

## Tests and scope

```sh
pytest
pytest tests/test_gui_support.py tests/test_gui_integration.py
qwave doctor --dev
```

Pure support tests run without Streamlit; AppTest integration tests are skipped
only when the optional dependency is absent. They check all four views,
no numerical work on slider edits, actual worker completion, stale-result labels,
data/plot export, saved-result reopening, exact cache behavior, cancellation,
privacy overrides, unit conversion and tamper rejection. The CLI independence
test actively blocks Streamlit imports. See `validation_stage6.md` for executed
checks and observed outcomes. UI verification does not replace the analytical,
conservation, quadrature and convergence tests in the numerical library.

Implementation references: [Streamlit local configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml),
[fragment polling](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment),
and [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
