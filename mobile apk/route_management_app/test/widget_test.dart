import "package:flutter_test/flutter_test.dart";
import "package:shared_preferences/shared_preferences.dart";

import "package:route_management_app/main.dart";

void main() {
  testWidgets("App opens login screen when no saved session", (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const RouteMasterDriverApp());
    await tester.pumpAndSettle();

    expect(find.text("ROUTEMASTER"), findsOneWidget);
    expect(find.text("Driver / Shop Owner Login"), findsOneWidget);
    expect(find.text("Login"), findsOneWidget);
  });
}
