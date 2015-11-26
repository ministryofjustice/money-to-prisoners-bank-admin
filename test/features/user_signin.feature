Feature: Signing in
  As a user
  I want to be able to sign in
  So that I can access the system

  Scenario: Successful sign in
    Given I am on the "Sign in" page
    When I sign in with "bank-admin" and "bank-admin"
    Then I should see "Logged in as Bank Admin"
