# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
# from django.db import models


# class Users(models.Model):
#     user_id = models.IntegerField(primary_key=True)
#     user_type = models.CharField(max_length=11)
#     user_name = models.CharField(max_length=30)
#     email = models.CharField(unique=True, max_length=255, blank=True, null=True)
#     balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
#     seller_rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
#     buyer_rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
#     num_of_seller_rating = models.IntegerField(blank=True, null=True)
#     num_of_buyer_rating = models.IntegerField(blank=True, null=True)
#     is_allowed_chat = models.IntegerField(blank=True, null=True)
#     is_allow_list = models.IntegerField(blank=True, null=True)

#     class Meta:
#         # managed = False
#         db_table = 'USERS'
