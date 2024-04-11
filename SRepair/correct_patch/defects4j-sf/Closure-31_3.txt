Node parseInputs() {
  boolean devMode = options.devMode != DevMode.OFF;

  // If old roots exist (we are parsing a second time), detach each of the
  // individual file parse trees.
  if (externsRoot != null) {
    externsRoot.detachChildren();
  }
  if (jsRoot != null) {
    jsRoot.detachChildren();
  }

  // Parse main js sources.
  jsRoot = IR.block();
  jsRoot.setIsSyntheticBlock(true);

  externsRoot = IR.block();
  externsRoot.setIsSyntheticBlock(true);

  externAndJsRoot = IR.block(externsRoot, jsRoot);
  externAndJsRoot.setIsSyntheticBlock(true);

  if (options.tracer.isOn()) {
    tracker = new PerformanceTracker(jsRoot, options.tracer);
    addChangeHandler(tracker.getCodeChangeHandler());
  }

  Tracer tracer = newTracer("parseInputs");

  try {
    // Parse externs sources.
    for (CompilerInput input : externs) {
      Node n = input.getAstRoot(this);
      if (hasErrors()) {
        return null;
      }
      externsRoot.addChildToBack(n);
    }

    // Modules inferred in ProcessCommonJS pass.
    if (options.transformAMDToCJSModules || options.processCommonJSModules) {
      processAMDAndCommonJSModules();
    }

    // Check if inputs need to be rebuilt from modules.
    boolean staleInputs = false;

    // Check if the sources need to be re-ordered.
    if (options.dependencyOptions.needsManagement() &&
        options.closurePass) {
      for (CompilerInput input : inputs) {
        // Forward-declare all the provided types, so that they
        // are not flagged even if they are dropped from the process.
        for (String provide : input.getProvides()) {
          getTypeRegistry().forwardDeclareType(provide);
        }
      }

      try {
        inputs =
            (moduleGraph == null ? new JSModuleGraph(modules) : moduleGraph)
            .manageDependencies(options.dependencyOptions, inputs);
        staleInputs = true;
      } catch (CircularDependencyException e) {
        report(JSError.make(
            JSModule.CIRCULAR_DEPENDENCY_ERROR, e.getMessage()));

        // If in IDE mode, we ignore the error and keep going.
        if (hasErrors()) {
          return null;
        }
      } catch (MissingProvideException e) {
        report(JSError.make(
            MISSING_ENTRY_ERROR, e.getMessage()));

        // If in IDE mode, we ignore the error and keep going.
        if (hasErrors()) {
          return null;
        }
      }
    }

    for (CompilerInput input : inputs) {
      Node n = input.getAstRoot(this);

      // Inputs can have a null AST during initial parse.
      if (n == null) {
        continue;
      }

      if (n.getJSDocInfo() != null) {
        JSDocInfo info = n.getJSDocInfo();
        if (info.isExterns()) {
          // If the input file is explicitly marked as an externs file, then
          // assume the programmer made a mistake and throw it into
          // the externs pile anyways.
          externsRoot.addChildToBack(n);
          input.setIsExtern(true);

          input.getModule().remove(input);

          externs.add(input);
          staleInputs = true;
        } else if (info.isNoCompile()) {
          input.getModule().remove(input);
          staleInputs = true;
        }
      }
    }

    if (staleInputs) {
      fillEmptyModules(modules);
      rebuildInputsFromModules();
    }

    // Build the AST.
    for (CompilerInput input : inputs) {
      Node n = input.getAstRoot(this);
      if (n == null) {
        continue;
      }

      if (devMode) {
        runSanityCheck();
        if (hasErrors()) {
          return null;
        }
      }

      if (options.sourceMapOutputPath != null ||
          options.nameReferenceReportPath != null) {

        // Annotate the nodes in the tree with information from the
        // input file. This information is used to construct the SourceMap.
        SourceInformationAnnotator sia =
            new SourceInformationAnnotator(
                input.getName(), options.devMode != DevMode.OFF);
        NodeTraversal.traverse(this, n, sia);
      }

      jsRoot.addChildToBack(n);
    }

    if (hasErrors()) {
      return null;
    }
    return externAndJsRoot;
  } finally {
    stopTracer(tracer, "parseInputs");
  }
}