/**
 * Runs the exported scikit-learn GradientBoostingRegressor in the browser.
 * prediction(log price) = init + learning_rate * Σ tree(x)   →   price = exp(prediction)
 */
(function (root) {
  function buildVector(model, input) {
    return model.features.map(function (name) {
      if (name.indexOf("cat__") === 0) {
        var rest = name.slice(5);
        for (var col in model.categories) {
          var prefix = col + "_";
          if (rest.indexOf(prefix) === 0) {
            return String(input[col]) === rest.slice(prefix.length) ? 1 : 0;
          }
        }
        return 0;
      }
      var key = name.replace(/^num__/, "");
      var v = input[key];
      if (typeof v === "boolean") v = v ? 1 : 0;
      return Number(v);
    });
  }

  function evalTree(tree, x) {
    var node = 0;
    while (tree.l[node] !== -1) {
      // scikit-learn compares in float32
      node = Math.fround(x[tree.f[node]]) <= tree.t[node] ? tree.l[node] : tree.r[node];
    }
    return tree.v[node];
  }

  function predictPrice(model, input) {
    var x = buildVector(model, input);
    var sum = 0;
    for (var i = 0; i < model.trees.length; i++) sum += evalTree(model.trees[i], x);
    return Math.exp(model.init + model.learning_rate * sum);
  }

  root.predictPrice = predictPrice;
  if (typeof module !== "undefined" && module.exports) module.exports = { predictPrice: predictPrice };
})(typeof window !== "undefined" ? window : this);
