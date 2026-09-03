{
  description = "tom-xs/portfolio -- monospace-web personal site (markdown -> pandoc -> HTML/PDF)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);

      pythonEnvFor = pkgs: pkgs.python3.withPackages (ps: [
        ps.weasyprint
        ps.watchdog
      ]);

      # Shared build inputs: pandoc for markdown->HTML, weasyprint (via python)
      # for the CV PDF, ruff for linting. weasyprint pulls in Pango/HarfBuzz/
      # Cairo transitively via nixpkgs, so no manual apt-style package list is
      # needed the way the GitHub Actions workflow needs it.
      runtimeInputsFor = pkgs: [
        pkgs.pandoc
        (pythonEnvFor pkgs)
        pkgs.ruff
      ];
    in
    {
      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = runtimeInputsFor pkgs;

            shellHook = ''
              echo "portfolio dev shell -- pandoc $(pandoc --version | head -n1 | awk '{print $2}'), $(python3 --version)"
              echo "run: python3 build.py            (build the site)"
              echo "run: python3 build.py --watch    (rebuild on change)"
              echo "run: ruff check build.py          (lint)"
            '';
          };
        });

      # `nix build` produces the fully built static site (HTML + CV PDF) as
      # $out, the same output the GitHub Actions workflow commits back to
      # the repo -- useful for verifying a build is reproducible outside CI.
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonEnv = pythonEnvFor pkgs;
        in
        {
          default = pkgs.stdenvNoCC.mkDerivation {
            pname = "portfolio-site";
            version = "0.0.0";
            src = self;

            nativeBuildInputs = [ pkgs.pandoc pythonEnv ];

            # weasyprint/fontconfig want a writable HOME and a font cache;
            # give it one and pull in a couple of common fonts so PDF text
            # renders consistently instead of falling back to missing-glyph
            # boxes on a from-scratch build sandbox.
            buildInputs = [ pkgs.dejavu_fonts pkgs.liberation_ttf ];

            buildPhase = ''
              runHook preBuild
              export HOME=$TMPDIR
              export FONTCONFIG_FILE=${pkgs.makeFontsConf {
                fontDirectories = [ pkgs.dejavu_fonts pkgs.liberation_ttf ];
              }}
              python3 build.py --output "$TMPDIR/out"
              runHook postBuild
            '';

            installPhase = ''
              runHook preInstall
              mkdir -p "$out"
              cp -r "$TMPDIR/out/." "$out/"
              runHook postInstall
            '';
          };
        });

      # `nix run` builds the site in place (same as `python3 build.py` in the
      # dev shell), for people who don't want to enter a shell first.
      apps = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pythonEnv = pythonEnvFor pkgs;
          runner = pkgs.writeShellApplication {
            name = "portfolio-build";
            runtimeInputs = [ pkgs.pandoc pythonEnv ];
            text = ''
              exec python3 build.py "$@"
            '';
          };
        in
        {
          default = {
            type = "app";
            program = "${runner}/bin/portfolio-build";
            meta = {
              description = "Build the portfolio site (wraps `python3 build.py`)";
              mainProgram = "portfolio-build";
            };
          };
        });

      # `nix flake check` runs the same lint the CI workflow runs, so a
      # broken build.py fails locally before it ever reaches GitHub Actions.
      checks = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          # `${self}` is a read-only Nix store path, so ruff can't write its
          # cache there -- point RUFF_CACHE_DIR at $TMPDIR instead of cd-ing
          # into the store and letting ruff pick a cache dir on its own.
          lint = pkgs.runCommand "ruff-check" { nativeBuildInputs = [ pkgs.ruff ]; } ''
            export RUFF_CACHE_DIR="$TMPDIR/ruff-cache"
            ruff check ${self}/build.py
            touch $out
          '';
        });

      formatter = forAllSystems (system:
        (import nixpkgs { inherit system; }).nixpkgs-fmt);
    };
}
