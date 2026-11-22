import 'dart:ui';

import 'package:ashur/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('con un pliegue vertical, la galaxia empieza a la derecha del pliegue', () {
    const pliegue = DisplayFeature(
      bounds: Rect.fromLTWH(400, 0, 0, 900),
      type: DisplayFeatureType.fold,
      state: DisplayFeatureState.postureFlat,
    );
    expect(margenPorPliegue([pliegue]), 400);
  });

  test('sin pliegue, o con uno horizontal, no se corre', () {
    expect(margenPorPliegue([]), 0);
    const horizontal = DisplayFeature(
      bounds: Rect.fromLTWH(0, 450, 800, 0),
      type: DisplayFeatureType.hinge,
      state: DisplayFeatureState.postureFlat,
    );
    expect(margenPorPliegue([horizontal]), 0);
    const recorte = DisplayFeature(
      bounds: Rect.fromLTWH(180, 0, 40, 30),
      type: DisplayFeatureType.cutout,
      state: DisplayFeatureState.unknown,
    );
    expect(margenPorPliegue([recorte]), 0);
  });
}
