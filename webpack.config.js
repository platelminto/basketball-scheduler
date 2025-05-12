const path = require("path");
const BundleTracker = require('webpack-bundle-tracker');

module.exports = {
  entry: {
    scheduleEdit: './assets/js/schedule-edit/index.js',
  },
  output: {
    path: path.resolve('./static/bundles/'),
    filename: "[name]-[hash].js",
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react']
          }
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new BundleTracker({filename: './webpack-stats.json'}),
  ],
};