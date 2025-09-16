# Contribution Guidelines

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs via [GitHub Issues](https://github.com/jannikmi/timezonefinder/issues).

When reporting a bug, please include:

- Your version of the package, Python, and Numba (if you use it)
- Any other details about your local setup that might be helpful in troubleshooting (for example, operating system)
- Detailed steps to reproduce the bug
- A detailed description of the bug (error log, stack trace, screenshots, etc.)

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "help wanted" and not assigned to anyone is open to whoever wants to implement it—leave a comment to say you have started working on it, and open a pull request as soon as you have something working so continuous integration can start building it.

Issues without "help wanted" generally already have some code ready in the background (maybe it is not yet open source), but you can still contribute to them by explaining how you would find the fix useful, linking to known prior art, or offering other relevant help.

### Write Documentation

Some features might have missing or unclear documentation. You can help improve it!

### Submit Feedback

The best way to send feedback is to file an issue via [GitHub Issues](https://github.com/jannikmi/timezonefinder/issues).

If you are proposing a feature:

- Explain in detail how it would work
- Keep the scope as narrow as possible to make it easier to implement (create multiple issues if necessary)
- Remember that this is a volunteer-driven project, and contributions are always welcome :)

## Get Started!

Ready to contribute? Here's how to set up this project for local development.

1. Fork this repo on GitHub.
2. Clone your fork locally.
3. Create a branch for local development:

   ```sh
   git checkout -b name-of-your-bugfix-or-feature
   ```

4. Review the instructions and notes in `publish.py`.
5. Install `tox` and run the tests:

   ```sh
   pip install tox
   tox
   ```

   The `tox.ini` file defines multiple test environments for different Python versions and for checking code style. During development of a feature or fix, you'll probably want to run just one environment plus the relevant code-style checks:

   ```sh
   tox -e codestyle
   ```

6. Commit your changes and push your branch to GitHub:

   ```sh
   git add .
   git commit -m "Your detailed description of your changes."
   git push origin name-of-your-bugfix-or-feature
   ```

7. Submit a pull request through the GitHub website. This will trigger the CI workflow, which runs the tests against all supported versions of Python.

Thank you for contributing!
